from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.common.settings import get_settings
from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAIProvider(BaseProvider):
    """OpenAI provider for AI jobs."""

    name = "openai"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult:
        """Generate text using OpenAI API."""
        model = str(kwargs.get("model", settings.OPENAI_MODEL_NAME))
        max_tokens = int(kwargs.get("max_tokens", 1024))  # type: ignore[arg-type]
        temperature = float(kwargs.get("temperature", 0.7))  # type: ignore[arg-type]

        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        tokens_used = response.usage.total_tokens if response.usage else 0

        return GenerateResult(
            text=choice.message.content or "",
            model=response.model,
            tokens_used=tokens_used,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            await self._client.models.list()
            return True
        except Exception as exc:
            logger.warning("openai health_check failed: %s", exc)
            return False
