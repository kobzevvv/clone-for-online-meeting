from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from src.stt.base import STTClient

logger = logging.getLogger(__name__)

_DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramSTT(STTClient):
    """Deepgram streaming STT client.

    Uses WebSocket for real-time streaming transcription.
    Requires DEEPGRAM_API_KEY environment variable.
    """

    def __init__(self, api_key: str, sample_rate: int = 16000) -> None:
        self.api_key = api_key
        self.sample_rate = sample_rate

    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        """Batch transcription via Deepgram REST API."""
        import httpx

        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/raw",
        }
        params = {
            "encoding": "linear16",
            "sample_rate": str(sample_rate),
            "channels": "1",
            "model": "nova-2",
            "language": "en",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url, content=audio, headers=headers, params=params
            )
            resp.raise_for_status()
            data = resp.json()

        transcript = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return transcript

    async def transcribe_stream(
        self, audio_iter: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """Stream audio to Deepgram via WebSocket and yield transcriptions."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets not installed, falling back to batch mode")
            async for text in super().transcribe_stream(audio_iter):
                yield text
            return

        params = (
            f"?encoding=linear16&sample_rate={self.sample_rate}"
            f"&channels=1&model=nova-2&language=en"
            f"&punctuate=true&interim_results=false"
        )
        url = _DEEPGRAM_WS_URL + params
        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                import asyncio

                async def send_audio() -> None:
                    async for chunk in audio_iter:
                        await ws.send(chunk)
                    # Signal end of audio
                    await ws.send(json.dumps({"type": "CloseStream"}))

                send_task = asyncio.create_task(send_audio())

                try:
                    async for msg in ws:
                        data = json.loads(msg)
                        if data.get("type") == "Results":
                            transcript = (
                                data.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                            )
                            if transcript.strip():
                                yield transcript
                finally:
                    send_task.cancel()
        except Exception:
            logger.exception("Deepgram WebSocket error, falling back to batch")
            async for text in super().transcribe_stream(audio_iter):
                yield text
