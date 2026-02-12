from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class STTClient(ABC):
    """Abstract base for speech-to-text providers."""

    @abstractmethod
    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        """Transcribe a complete audio buffer to text."""
        ...

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """Transcribe streaming audio. Default: accumulate then batch-transcribe."""
        chunks: list[bytes] = []
        async for chunk in audio_iter:
            chunks.append(chunk)
        if chunks:
            audio = b"".join(chunks)
            result = await self.transcribe(audio)
            if result.strip():
                yield result
