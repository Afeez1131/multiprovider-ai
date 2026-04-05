from __future__ import annotations

import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.base import GenerateResult
from app.providers.router import ProviderRouter


# ---------------------------------------------------------------------------
# ProviderRouter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_calls_provider_and_returns_result() -> None:
    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.generate = AsyncMock(
        return_value=GenerateResult(text="hello", model="m1", tokens_used=5, provider="mock")
    )

    router = ProviderRouter(mock_provider)
    result = await router.generate("test prompt")

    assert result.provider == "mock"
    assert result.text == "hello"
    mock_provider.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_router_propagates_provider_error() -> None:
    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("provider down"))

    router = ProviderRouter(mock_provider)

    with pytest.raises(RuntimeError, match="provider down"):
        await router.generate("test prompt")


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_generate() -> None:
    from app.providers.ollama_provider import OllamaProvider
    import app.providers.ollama_provider as ollama_mod

    mock_settings = MagicMock()
    mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"

    with patch.object(ollama_mod, "settings", mock_settings):
        provider = OllamaProvider()
        with respx.mock:
            respx.post("http://localhost:11434/api/generate").mock(
                return_value=Response(
                    200,
                    json={
                        "response": "test output",
                        "eval_count": 10,
                        "prompt_eval_count": 5,
                    },
                )
            )
            result = await provider.generate("hello", model="llama3.2")

    assert result.text == "test output"
    assert result.tokens_used == 15
    assert result.provider == "ollama"


@pytest.mark.asyncio
async def test_ollama_health_check_ok() -> None:
    from app.providers.ollama_provider import OllamaProvider
    import app.providers.ollama_provider as ollama_mod

    mock_settings = MagicMock()
    mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"

    with patch.object(ollama_mod, "settings", mock_settings):
        provider = OllamaProvider()
        with respx.mock:
            respx.get("http://localhost:11434/api/tags").mock(
                return_value=Response(200, json={"models": []})
            )
            ok = await provider.health_check()

    assert ok is True


@pytest.mark.asyncio
async def test_ollama_health_check_fail() -> None:
    from app.providers.ollama_provider import OllamaProvider
    import app.providers.ollama_provider as ollama_mod

    mock_settings = MagicMock()
    mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"

    with patch.object(ollama_mod, "settings", mock_settings):
        provider = OllamaProvider()
        with respx.mock:
            respx.get("http://localhost:11434/api/tags").mock(side_effect=Exception("conn refused"))
            ok = await provider.health_check()

    assert ok is False


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_job_idempotency(db: object) -> None:
    """Calling _process_job_async twice with same job_id only processes once."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Job, JobStatus
    from app.workers.tasks import _process_job_async
    import app.providers.router as router_module

    assert isinstance(db, AsyncSession)

    job = Job(prompt="idempotency test")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id

    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.generate = AsyncMock(
        return_value=GenerateResult(
            text="result", model="m", tokens_used=1, provider="mock"
        )
    )
    router_module.router = ProviderRouter(mock_provider)

    with patch("app.workers.tasks.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.workers.tasks.build_router", return_value=router_module.router):
            await _process_job_async(job_id)

        await db.refresh(job)
        assert job.status == JobStatus.COMPLETED

        # Second call — idempotency guard should skip processing
        mock_provider.generate.reset_mock()
        with patch("app.workers.tasks.build_router", return_value=router_module.router):
            await _process_job_async(job_id)

    mock_provider.generate.assert_not_called()
