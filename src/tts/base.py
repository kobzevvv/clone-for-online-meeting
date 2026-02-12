from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TTSClient(ABC):
    """Abstract base for text-to-speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (PCM 16-bit, 24kHz, mono)."""
        ...

    @abstractmethod
    async def synthesize_stream(
        self, text_iter: AsyncIterator[str]
    ) -> AsyncIterator[bytes]:
        """Convert streaming text tokens to streaming audio chunks."""
        ...
