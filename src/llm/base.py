from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def stream_completion(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Yield text tokens as they stream from the model."""
        ...

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming convenience wrapper."""
        parts: list[str] = []
        async for token in self.stream_completion(messages):
            parts.append(token)
        return "".join(parts)
