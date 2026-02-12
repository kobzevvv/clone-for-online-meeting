from __future__ import annotations

import asyncio
import io
import logging
import threading
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Audio playback with barge-in support.

    Plays audio through the default output device.
    Can be interrupted (barge-in) at any time.
    """

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self._playing = False
        self._stop_event = threading.Event()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def stop(self) -> None:
        """Interrupt playback immediately (barge-in)."""
        if self._playing:
            self._stop_event.set()
            logger.debug("Playback interrupted (barge-in)")

    async def play_bytes(self, audio_data: bytes) -> None:
        """Play raw audio bytes (expects mp3 or raw PCM)."""
        if not audio_data:
            return
        self._playing = True
        self._stop_event.clear()
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._play_sync, audio_data
            )
        finally:
            self._playing = False

    async def play_stream(self, audio_iter: AsyncIterator[bytes]) -> None:
        """Play streaming audio chunks. Stops on barge-in."""
        self._playing = True
        self._stop_event.clear()
        try:
            buffer = io.BytesIO()
            async for chunk in audio_iter:
                if self._stop_event.is_set():
                    logger.debug("Stream playback interrupted")
                    break
                buffer.write(chunk)
                # Play accumulated audio when buffer is large enough
                if buffer.tell() >= 8192:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._play_sync, buffer.getvalue()
                    )
                    buffer = io.BytesIO()
            # Play remaining buffer
            if buffer.tell() > 0 and not self._stop_event.is_set():
                await asyncio.get_event_loop().run_in_executor(
                    None, self._play_sync, buffer.getvalue()
                )
        finally:
            self._playing = False

    def _play_sync(self, data: bytes) -> None:
        """Synchronous playback. Tries sounddevice first, falls back to logging."""
        if self._stop_event.is_set():
            return
        try:
            import sounddevice as sd
            import numpy as np

            # Try to decode as mp3 first (ElevenLabs returns mp3)
            try:
                audio_array = self._decode_mp3(data)
            except Exception:
                # Assume raw PCM 16-bit
                audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

            if len(audio_array) == 0:
                return

            sd.play(audio_array, self.sample_rate)
            # Wait for playback with periodic stop checks
            while sd.get_stream().active:
                if self._stop_event.is_set():
                    sd.stop()
                    return
                self._stop_event.wait(timeout=0.05)
            sd.wait()
        except ImportError:
            logger.warning("sounddevice not available, skipping playback")
        except Exception:
            logger.exception("Playback error")

    @staticmethod
    def _decode_mp3(data: bytes) -> "np.ndarray":
        """Decode mp3 bytes to numpy float32 array."""
        import io
        import numpy as np

        try:
            # Try using pydub if available
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(data))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples /= 2 ** (audio.sample_width * 8 - 1)
            return samples
        except ImportError:
            # If pydub not available, raise to fall back to PCM
            raise
