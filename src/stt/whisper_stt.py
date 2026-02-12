from __future__ import annotations

import io
import logging
import tempfile
import wave
from collections.abc import AsyncIterator

import numpy as np

from src.stt.base import STTClient

logger = logging.getLogger(__name__)


class WhisperSTT(STTClient):
    """Local STT using faster-whisper."""

    def __init__(self, model_size: str = "base") -> None:
        self._model = None
        self._model_size = model_size

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
            logger.info("Loading Whisper model: %s", self._model_size)
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded")
        except ImportError:
            raise RuntimeError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )

    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM 16-bit audio bytes."""
        self._ensure_model()

        # Convert raw PCM bytes to WAV in memory
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio)

        # faster-whisper needs a file path or numpy array
        wav_buf.seek(0)
        audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        segments, info = self._model.transcribe(
            audio_array,
            beam_size=1,
            language="en",
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        logger.debug("Whisper transcription: %s", text[:100])
        return text

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """Accumulate audio then transcribe (Whisper is not truly streaming)."""
        chunks: list[bytes] = []
        async for chunk in audio_iter:
            chunks.append(chunk)
        if chunks:
            audio = b"".join(chunks)
            result = await self.transcribe(audio)
            if result.strip():
                yield result


class DummySTT(STTClient):
    """Fallback STT that returns empty transcriptions.

    Use when no STT provider is available. Useful for text-only mode testing.
    """

    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        logger.info("[DummySTT] Received %d bytes of audio", len(audio))
        return ""

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        async for _ in audio_iter:
            pass
        yield ""
