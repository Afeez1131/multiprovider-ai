from __future__ import annotations

import logging

import httpx

from app.common.settings import get_settings
from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult:
        model = str(kwargs.get("model", "llama3.2"))

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()

        text = data.get("response", "")
        tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

        return GenerateResult(
            text=text,
            model=model,
            tokens_used=tokens_used,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception as exc:
            logger.warning("ollama health_check failed: %s", exc)
            return False
