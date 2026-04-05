from __future__ import annotations

import logging

import anthropic

from app.common.settings import get_settings
from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)
settings = get_settings()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult:
        """Generate text using Anthropic API."""
        model = str(kwargs.get("model", settings.ANTHROPIC_MODEL_NAME))
        max_tokens = int(kwargs.get("max_tokens", 1024))  # type: ignore[arg-type]

        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        tokens_used = (
            response.usage.input_tokens + response.usage.output_tokens
            if response.usage
            else 0
        )

        return GenerateResult(
            text=text,
            model=response.model,
            tokens_used=tokens_used,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        """Check if Anthropic API is available."""
        try:
            await self._client.messages.create(
                model=settings.ANTHROPIC_MODEL_NAME,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception as exc:
            logger.warning("anthropic health_check failed: %s", exc)
            return False
