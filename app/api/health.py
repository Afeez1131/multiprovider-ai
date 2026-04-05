from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from app.common.database import AsyncSessionLocal
from app.common.settings import get_settings
from app.providers.router import router as provider_router

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    """Check the health of the application and its dependencies."""
    # Check database
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("database health check failed: %s", exc)

    # Check Redis
    redis_ok = False
    try:

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception as exc:
        logger.warning("redis health check failed: %s", exc)

    # Check providers
    provider_statuses: dict[str, bool] = {}
    try:

        if provider_router is not None:
            p = provider_router.provider
            try:
                provider_statuses[p.name] = await p.health_check()
            except Exception as exc:
                logger.warning("provider=%s health_check error: %s", p.name, exc)
                provider_statuses[p.name] = False
    except Exception as exc:
        logger.warning("provider health checks failed: %s", exc)

    return {
        "status": "ok",
        "providers": provider_statuses,
        "redis": redis_ok,
        "database": db_ok,
    }
