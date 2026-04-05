from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import JobStatus


class JobCreateRequest(BaseModel):
    prompt: str
    options: dict[str, object] | None = None
    callback_url: str | None = None


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: JobStatus
    created_at: datetime

    @classmethod
    def from_orm(cls, job: object) -> JobCreateResponse:  # type: ignore[override]
        from app.models import Job

        j = job  # type: ignore[assignment]
        assert isinstance(j, Job)
        return cls(job_id=j.id, status=j.status, created_at=j.created_at)


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    provider_used: str | None = None
    model_used: str | None = None
    tokens_used: int | None = None

    @classmethod
    def from_orm(cls, job: object) -> JobStatusResponse:  # type: ignore[override]
        from app.models import Job

        j = job  # type: ignore[assignment]
        assert isinstance(j, Job)
        return cls(
            job_id=j.id,
            status=j.status,
            created_at=j.created_at,
            completed_at=j.completed_at,
            result=j.result,
            error=j.error,
            provider_used=j.provider_used,
            model_used=j.model_used,
            tokens_used=j.tokens_used,
        )
