from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.models import Job
from app.schemas import JobCreateRequest, JobCreateResponse, JobStatusResponse
from app.workers.tasks import process_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/jobs", tags=["jobs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreateResponse)
async def create_job(
    body: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
) -> JobCreateResponse:
    job = Job(
        prompt=body.prompt,
        options=body.options,
        callback_url=body.callback_url,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    process_job.delay(job.id)
    logger.info("job_id=%s enqueued", job.id)

    return JobCreateResponse.from_orm(job)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
) -> JobStatusResponse:
    # Check Redis cache first
    import json

    from app.common.cache import get_cached_result, make_cache_key
    from app.models import JobStatus

    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job not found"
        )

    # Only serve from cache when the job is completed
    if job.status == JobStatus.COMPLETED and job.options is not None:
        cache_key = make_cache_key(job.prompt, job.options)
        cached = await get_cached_result(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                job.result = cached_data.get("result", job.result)
            except Exception:
                pass  # fall through to DB value

    return JobStatusResponse.from_orm(job)
