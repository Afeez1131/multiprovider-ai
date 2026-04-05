from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerateResult:
    text: str
    model: str
    tokens_used: int
    provider: str


class BaseProvider(ABC):
    """Base class for all AI providers."""
    name: str

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: object) -> GenerateResult: ...

    async def health_check(self) -> bool:
        """Ping the provider. Returns True if reachable."""
        return True
