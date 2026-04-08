from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.common.settings import get_settings
from app.models import Job, JobStatus, UsageLog
from app.providers.router import build_router
from app.workers.broker import celery_app

logger = logging.getLogger(__name__)


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create a fresh engine + session factory bound to the current event loop."""
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        poolclass=NullPool,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(
    name="process_job",
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    acks_late=True,
)
def process_job(self: object, job_id: str) -> None:
    """Celery task entry point — delegates to async implementation."""
    asyncio.run(_process_job_async(job_id))


async def _process_job_async(job_id: str) -> None:
    AsyncSessionLocal = _make_session_factory()
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)

        if job is None:
            logger.warning("job_id=%s not found — skipping", job_id)
            return

        if job.status != JobStatus.PENDING:
            logger.warning(
                "job_id=%s status=%s — idempotency guard triggered",
                job_id,
                job.status,
            )
            return

        job.status = JobStatus.PROCESSING
        await db.commit()

        try:
            _router = build_router(get_settings().DEFAULT_PROVIDER)
            options: dict[str, object] = job.options or {}
            result = await _router.generate(job.prompt, **options)

            job.status = JobStatus.COMPLETED
            job.result = result.text
            job.provider_used = result.provider
            job.tokens_used = result.tokens_used
            job.model_used = result.model
            job.completed_at = datetime.utcnow()

            usage = UsageLog(
                job_id=job.id,
                provider=result.provider,
                model=result.model,
                tokens_used=result.tokens_used,
            )
            db.add(usage)

            logger.info(
                "job_id=%s completed provider=%s tokens=%s",
                job_id,
                result.provider,
                result.tokens_used,
            )

        except Exception as exc:
            logger.error("job_id=%s failed: %s", job_id, exc)
            job.status = JobStatus.FAILED
            job.error = str(exc)

        finally:
            await db.commit()

    if job.status == JobStatus.COMPLETED and job.callback_url:
        await _fire_webhook(job)


async def _fire_webhook(job: Job) -> None:
    payload = {
        "job_id": str(job.id),
        "status": job.status,
        "result": job.result,
        "provider_used": job.provider_used,
        "tokens_used": job.tokens_used,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode()

    _settings = get_settings()
    headers: dict[str, str] = {}
    if _settings.WEBHOOK_SECRET:
        sig = hmac.new(
            _settings.WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = sig

    try:
        async with httpx.AsyncClient(timeout=_settings.WEBHOOK_TIMEOUT_SECONDS) as client:
            await client.post(str(job.callback_url), content=payload_bytes, headers=headers)
            logger.info("job_id=%s webhook delivered", job.id)
    except Exception as exc:
        logger.warning("job_id=%s webhook failed: %s", job.id, exc)
