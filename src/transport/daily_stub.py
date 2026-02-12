from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from src.transport.base import TransportAdapter

logger = logging.getLogger(__name__)


class DailyTransport(TransportAdapter):
    """Stub transport adapter for Daily.co video calls.

    TODO: Implement using daily-python SDK.
    See: https://docs.daily.co/reference/daily-python

    Integration points:
    - Join a Daily room via room URL
    - Receive participant audio via on_audio_data callback
    - Send audio via send_audio() or send_app_message()
    - Handle participant join/leave events
    """

    def __init__(self, room_url: str = "", token: str = "") -> None:
        self.room_url = room_url
        self.token = token
        logger.warning("DailyTransport is a stub — not yet implemented")

    async def start(self) -> None:
        raise NotImplementedError(
            "DailyTransport is not yet implemented. "
            "Install daily-python and implement room joining logic."
        )

    async def stop(self) -> None:
        raise NotImplementedError

    async def read_audio_frames(self) -> AsyncIterator[bytes]:
        raise NotImplementedError
        yield b""  # type: ignore[misc]  # make it a generator

    async def write_audio(self, data: bytes) -> None:
        raise NotImplementedError

    async def write_audio_stream(self, audio_iter: AsyncIterator[bytes]) -> None:
        raise NotImplementedError

    def stop_playback(self) -> None:
        raise NotImplementedError

    def is_playing(self) -> bool:
        return False
