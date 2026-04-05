from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Single default provider — one of: openai, anthropic, gemini, ollama
    DEFAULT_PROVIDER: str = "gemini"

    # Provider API keys
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = ""
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL_NAME: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Infrastructure
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/aibackend"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth — empty string disables auth in dev; comma-separated list of valid keys
    API_KEY_HEADER: str = "X-API-Key"
    api_keys_raw: str = Field(default="", validation_alias="API_KEYS")

    # Webhooks
    WEBHOOK_SECRET: str = ""
    WEBHOOK_TIMEOUT_SECONDS: int = 10

    # Caching
    RESULT_CACHE_TTL_SECONDS: int = 3600

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    model_config = {"env_file": ".env", "populate_by_name": True}

    @property
    def API_KEYS(self) -> list[str]:
        raw = self.api_keys_raw.strip()
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
