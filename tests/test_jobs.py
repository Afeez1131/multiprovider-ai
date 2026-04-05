from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /ai/jobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_job_returns_202(client: AsyncClient) -> None:
    with patch("app.api.jobs.process_job") as mock_actor:
        mock_actor.send = MagicMock()
        response = await client.post("/ai/jobs", json={"prompt": "Hello world"})

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "job_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_job_missing_prompt_returns_422(client: AsyncClient) -> None:
    response = await client.post("/ai/jobs", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_job_with_options(client: AsyncClient) -> None:
    with patch("app.api.jobs.process_job") as mock_actor:
        mock_actor.send = MagicMock()
        response = await client.post(
            "/ai/jobs",
            json={
                "prompt": "Summarise this",
                "options": {"model": "gpt-4o-mini", "max_tokens": 100},
                "callback_url": "https://example.com/webhook",
            },
        )

    assert response.status_code == 202


# ---------------------------------------------------------------------------
# GET /ai/jobs/{job_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient) -> None:
    response = await client.get("/ai/jobs/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "job not found"


@pytest.mark.asyncio
async def test_get_job_pending(client: AsyncClient, db: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Job

    assert isinstance(db, AsyncSession)

    job = Job(prompt="test")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    response = await client.get(f"/ai/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["status"] == "pending"
    assert data["result"] is None


@pytest.mark.asyncio
async def test_get_job_completed(client: AsyncClient, db: object) -> None:
    from datetime import datetime
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Job, JobStatus

    assert isinstance(db, AsyncSession)

    job = Job(
        prompt="test",
        status=JobStatus.COMPLETED,
        result="done",
        provider_used="openai",
        model_used="gpt-4o-mini",
        tokens_used=10,
        completed_at=datetime.utcnow(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    response = await client.get(f"/ai/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == "done"
    assert data["provider_used"] == "openai"
    assert data["tokens_used"] == 10


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_required_when_api_keys_set(client: AsyncClient) -> None:
    with patch("app.common.deps.settings") as mock_settings:
        mock_settings.API_KEYS = ["secret-key"]

        response = await client.post("/ai/jobs", json={"prompt": "test"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_passes_with_correct_key(client: AsyncClient) -> None:
    with patch("app.common.deps.settings") as mock_settings:
        mock_settings.API_KEYS = ["secret-key"]
        mock_settings.API_KEY_HEADER = "X-API-Key"

        with patch("app.api.jobs.process_job") as mock_actor:
            mock_actor.send = MagicMock()
            response = await client.post(
                "/ai/jobs",
                json={"prompt": "test"},
                headers={"X-API-Key": "secret-key"},
            )

    assert response.status_code == 202


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "redis" in data
    assert "database" in data
    assert "providers" in data
