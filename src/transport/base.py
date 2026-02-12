from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Callable


class TransportAdapter(ABC):
    """Abstract transport layer for audio I/O.

    Implementations provide audio input/output for different environments:
    - LocalAudioTransport: mic + speakers via sounddevice
    - DailyTransport: Daily.co video calls (stub)
    - LiveKitTransport: LiveKit rooms (stub)
    """

    @abstractmethod
    async def start(self) -> None:
        """Initialize and start the transport."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop and clean up the transport."""
        ...

    @abstractmethod
    async def read_audio_frames(self) -> AsyncIterator[bytes]:
        """Yield raw PCM audio frames from the input source."""
        ...

    @abstractmethod
    async def write_audio(self, data: bytes) -> None:
        """Send audio data to the output (speakers/call)."""
        ...

    @abstractmethod
    async def write_audio_stream(self, audio_iter: AsyncIterator[bytes]) -> None:
        """Stream audio data to the output."""
        ...

    @abstractmethod
    def stop_playback(self) -> None:
        """Interrupt current audio output (barge-in)."""
        ...

    @abstractmethod
    def is_playing(self) -> bool:
        """Whether audio is currently being played."""
        ...
