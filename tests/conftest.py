from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base
from app.providers.base import GenerateResult


# ---------------------------------------------------------------------------
# In-memory SQLite database for tests
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def create_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Override DB dependency in the FastAPI app
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(db: AsyncSession) -> AsyncClient:
    from app.main import app
    from app.common.deps import get_db

    async def override_get_db() -> AsyncSession:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Stub out the provider router so tests don't need real API keys
    from app.providers.router import ProviderRouter
    import app.providers.router as router_module
    from unittest.mock import AsyncMock

    mock_provider = AsyncMock()
    mock_provider.name = "mock"
    mock_provider.generate = AsyncMock(
        return_value=GenerateResult(
            text="mocked response",
            model="mock-model",
            tokens_used=42,
            provider="mock",
        )
    )
    mock_provider.health_check = AsyncMock(return_value=True)
    router_module.router = ProviderRouter(mock_provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared fixture: a canned GenerateResult
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_result() -> GenerateResult:
    return GenerateResult(
        text="mocked response",
        model="mock-model",
        tokens_used=42,
        provider="mock",
    )
