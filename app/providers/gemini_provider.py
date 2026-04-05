from __future__ import annotations

import asyncio
import logging

import google.generativeai as genai

from app.common.settings import get_settings
from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider(BaseProvider):
    """Gemini provider for AI jobs."""
    name = "gemini"

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=settings.GEMINI_API_KEY)

    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult:
        """Generate text using Gemini API."""
        model_name = str(kwargs.get("model", settings.GEMINI_MODEL_NAME))
        model = genai.GenerativeModel(model_name)

        # SDK is sync — run in thread pool to avoid blocking the event loop
        response = await asyncio.to_thread(model.generate_content, prompt)

        text = response.text or ""
        tokens_used = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_used = getattr(response.usage_metadata, "total_token_count", 0)

        return GenerateResult(
            text=text,
            model=model_name,
            tokens_used=tokens_used,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        """Check if Gemini API is available."""
        try:
            models = await asyncio.to_thread(lambda: list(genai.list_models()))
            return len(models) > 0
        except Exception as exc:
            logger.warning("gemini health_check failed: %s", exc)
            return False
