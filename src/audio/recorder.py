from __future__ import annotations

import asyncio
import logging
import queue
import threading

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Microphone audio capture using sounddevice.

    Captures audio in frames suitable for VAD processing.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        frame_duration_ms: int = 30,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._running = False
        self._stream = None

    async def start(self) -> None:
        """Start recording from microphone."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            raise

        self._running = True

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning("Audio input status: %s", status)
            self._queue.put(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.frame_size,
            dtype="int16",
            channels=self.channels,
            callback=callback,
        )
        self._stream.start()
        logger.info(
            "Recording started: %dHz, %dch, frame=%d samples",
            self.sample_rate,
            self.channels,
            self.frame_size,
        )

    async def stop(self) -> None:
        """Stop recording."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("Recording stopped")

    async def read_frame(self) -> bytes | None:
        """Read the next audio frame. Returns None if not running."""
        if not self._running:
            return None
        try:
            # Non-blocking with small timeout to allow cooperative scheduling
            loop = asyncio.get_event_loop()
            frame = await loop.run_in_executor(
                None, lambda: self._queue.get(timeout=0.1)
            )
            return frame
        except queue.Empty:
            return None

    async def read_frames(self):
        """Async generator yielding audio frames."""
        while self._running:
            frame = await self.read_frame()
            if frame is not None:
                yield frame
