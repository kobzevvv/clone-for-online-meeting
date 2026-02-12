from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from src.transport.base import TransportAdapter

logger = logging.getLogger(__name__)


class LiveKitTransport(TransportAdapter):
    """Stub transport adapter for LiveKit rooms.

    TODO: Implement using livekit SDK.
    See: https://docs.livekit.io/realtime/

    Integration points:
    - Connect to a LiveKit room via URL + token
    - Subscribe to participant audio tracks
    - Publish audio track for agent output
    - Handle track subscription events
    """

    def __init__(self, url: str = "", token: str = "") -> None:
        self.url = url
        self.token = token
        logger.warning("LiveKitTransport is a stub — not yet implemented")

    async def start(self) -> None:
        raise NotImplementedError(
            "LiveKitTransport is not yet implemented. "
            "Install livekit SDK and implement room connection logic."
        )

    async def stop(self) -> None:
        raise NotImplementedError

    async def read_audio_frames(self) -> AsyncIterator[bytes]:
        raise NotImplementedError
        yield b""  # type: ignore[misc]

    async def write_audio(self, data: bytes) -> None:
        raise NotImplementedError

    async def write_audio_stream(self, audio_iter: AsyncIterator[bytes]) -> None:
        raise NotImplementedError

    def stop_playback(self) -> None:
        raise NotImplementedError

    def is_playing(self) -> bool:
        return False
