from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from src.audio.player import AudioPlayer
from src.audio.recorder import AudioRecorder
from src.transport.base import TransportAdapter

logger = logging.getLogger(__name__)


class LocalAudioTransport(TransportAdapter):
    """Local mic + speakers transport using sounddevice."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30) -> None:
        self.recorder = AudioRecorder(
            sample_rate=sample_rate,
            frame_duration_ms=frame_duration_ms,
        )
        self.player = AudioPlayer(sample_rate=24000)  # ElevenLabs outputs 24kHz

    async def start(self) -> None:
        await self.recorder.start()
        logger.info("Local audio transport started")

    async def stop(self) -> None:
        await self.recorder.stop()
        logger.info("Local audio transport stopped")

    async def read_audio_frames(self) -> AsyncIterator[bytes]:
        async for frame in self.recorder.read_frames():
            yield frame

    async def write_audio(self, data: bytes) -> None:
        await self.player.play_bytes(data)

    async def write_audio_stream(self, audio_iter: AsyncIterator[bytes]) -> None:
        await self.player.play_stream(audio_iter)

    def stop_playback(self) -> None:
        self.player.stop()

    def is_playing(self) -> bool:
        return self.player.is_playing
