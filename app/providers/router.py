from __future__ import annotations

import logging

from app.providers.base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)

# Module-level singleton — set during app/worker startup
router: ProviderRouter | None = None


class ProviderRouter:
    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult:
        result = await self.provider.generate(prompt, **kwargs)
        logger.info("provider=%s success", self.provider.name)
        return result


def build_router(provider_name: str) -> ProviderRouter:
    """Instantiate the named provider and return a ProviderRouter."""
    from app.providers.anthropic_provider import AnthropicProvider
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.ollama_provider import OllamaProvider
    from app.providers.openai_provider import OpenAIProvider

    provider_map: dict[str, type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
    }

    cls = provider_map.get(provider_name)
    if cls is None:
        raise RuntimeError(
            f"Unknown provider '{provider_name}'. "
            f"Valid options: {', '.join(provider_map)}"
        )

    return ProviderRouter(cls())
