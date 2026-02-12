from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from src.tts.base import TTSClient

logger = logging.getLogger(__name__)

# ElevenLabs streaming TTS endpoint
_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
_TTS_URL_NON_STREAM = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsTTS(TTSClient):
    """ElevenLabs TTS with HTTP streaming support."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_turbo_v2_5",
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self._headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

    async def synthesize(self, text: str) -> bytes:
        """Synthesize complete text to audio bytes."""
        url = _TTS_URL_NON_STREAM.format(voice_id=self.voice_id)
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers)
            resp.raise_for_status()
            return resp.content

    async def synthesize_stream(
        self, text_iter: AsyncIterator[str]
    ) -> AsyncIterator[bytes]:
        """Accumulate text into sentences, then stream audio for each sentence.

        ElevenLabs streaming endpoint accepts complete text and returns audio
        in chunks. We accumulate LLM tokens into sentences, then request
        audio for each sentence to keep latency low.
        """
        sentence_buffer = ""
        sentence_delimiters = {".", "!", "?", "\n"}

        async for token in text_iter:
            sentence_buffer += token
            # Check if we have a complete sentence
            if any(d in token for d in sentence_delimiters) and len(sentence_buffer.strip()) > 10:
                sentence = sentence_buffer.strip()
                sentence_buffer = ""
                async for audio_chunk in self._stream_sentence(sentence):
                    yield audio_chunk

        # Flush remaining text
        if sentence_buffer.strip():
            async for audio_chunk in self._stream_sentence(sentence_buffer.strip()):
                yield audio_chunk

    async def _stream_sentence(self, text: str) -> AsyncIterator[bytes]:
        """Stream audio for a single sentence from ElevenLabs."""
        url = _TTS_URL.format(voice_id=self.voice_id)
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        logger.debug("TTS streaming sentence: %s", text[:50])
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=self._headers
                ) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        yield chunk
        except httpx.HTTPError:
            logger.exception("TTS streaming failed for: %s", text[:50])


class DummyTTS(TTSClient):
    """Fallback TTS that logs text instead of producing audio.

    Use when no TTS API key is configured.
    """

    async def synthesize(self, text: str) -> bytes:
        logger.info("[DummyTTS] Would speak: %s", text)
        return b""

    async def synthesize_stream(
        self, text_iter: AsyncIterator[str]
    ) -> AsyncIterator[bytes]:
        full_text: list[str] = []
        async for token in text_iter:
            full_text.append(token)
        logger.info("[DummyTTS] Would speak: %s", "".join(full_text))
        # Yield empty bytes so the async iterator protocol is satisfied
        yield b""
