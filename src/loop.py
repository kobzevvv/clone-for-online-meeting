from __future__ import annotations

import asyncio
import logging
import time

from src.agent.agent import InterviewAgent
from src.audio.vad import EnergyVAD
from src.stt.base import STTClient
from src.transport.base import TransportAdapter
from src.tts.base import TTSClient

logger = logging.getLogger(__name__)


class VoiceLoop:
    """Real-time voice interaction loop.

    Flow: Transport(mic) -> VAD -> STT -> Agent -> TTS -> Transport(speakers)
    Supports barge-in: if user speaks during TTS playback, stop and listen.
    """

    def __init__(
        self,
        agent: InterviewAgent,
        stt: STTClient,
        tts: TTSClient,
        transport: TransportAdapter,
        vad: EnergyVAD,
    ) -> None:
        self.agent = agent
        self.stt = stt
        self.tts = tts
        self.transport = transport
        self.vad = vad
        self._running = False

    async def run(self) -> None:
        """Start the voice interaction loop."""
        self._running = True
        await self.transport.start()
        logger.info("Voice loop started. Speak into your microphone...")
        print("\n🎤 Listening... (Ctrl+C to stop)\n")

        try:
            while self._running:
                # Collect utterance via VAD
                audio_buffer = await self._collect_utterance()
                if audio_buffer is None:
                    continue

                t_start = time.monotonic()

                # Transcribe
                transcript = await self.stt.transcribe(audio_buffer)
                t_stt = time.monotonic()

                if not transcript.strip():
                    logger.debug("Empty transcription, skipping")
                    continue

                logger.info("STT (%.0fms): %s", (t_stt - t_start) * 1000, transcript)
                print(f"\n👤 You: {transcript}")

                # Generate and speak response
                await self._generate_and_speak(transcript, t_start)

        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the voice loop."""
        self._running = False
        await self.transport.stop()
        logger.info("Voice loop stopped")

    async def _collect_utterance(self) -> bytes | None:
        """Collect audio frames until end-of-utterance detected by VAD."""
        audio_chunks: list[bytes] = []
        collecting = False

        async for frame in self.transport.read_audio_frames():
            if not self._running:
                return None

            event = self.vad.process_frame(frame)

            # Barge-in: if user speaks during playback, stop it
            if event in ("speech_start", "speech") and self.transport.is_playing():
                logger.info("Barge-in detected, stopping playback")
                self.transport.stop_playback()

            if event == "speech_start":
                collecting = True
                audio_chunks = [frame]
            elif event == "speech" and collecting:
                audio_chunks.append(frame)
            elif event == "speech_end" and collecting:
                audio_chunks.append(frame)
                self.vad.reset()
                return b"".join(audio_chunks)

        return None

    async def _generate_and_speak(self, transcript: str, t_start: float) -> None:
        """Generate agent response and stream TTS output."""
        print("🤖 Agent: ", end="", flush=True)

        # Collect response text for display and TTS
        full_response: list[str] = []

        async def text_stream():
            async for token in self.agent.respond_stream(transcript):
                full_response.append(token)
                print(token, end="", flush=True)
                yield token

        # Stream text through TTS and play audio
        try:
            audio_stream = self.tts.synthesize_stream(text_stream())
            await self.transport.write_audio_stream(audio_stream)
        except Exception:
            logger.exception("TTS/playback error")

        t_end = time.monotonic()
        print()  # newline after response
        logger.info(
            "Total turn time: %.0fms",
            (t_end - t_start) * 1000,
        )


class TextLoop:
    """Text-only interaction loop for testing without audio hardware."""

    def __init__(self, agent: InterviewAgent, tts: TTSClient | None = None) -> None:
        self.agent = agent
        self.tts = tts

    async def run(self) -> None:
        """Run the text interaction loop."""
        print("\n💬 Text mode — type your questions (Ctrl+C or 'quit' to exit)\n")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("👤 You: ")
                )
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if user_input.strip().lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            print("🤖 Agent: ", end="", flush=True)
            full_response: list[str] = []
            async for token in self.agent.respond_stream(user_input):
                full_response.append(token)
                print(token, end="", flush=True)
            print()

            # Optional: play TTS
            if self.tts:
                try:
                    response_text = "".join(full_response)
                    # Only speak the answer part, not the sources
                    answer_part = response_text.split("Sources:")[0].strip()
                    if answer_part:
                        audio = await self.tts.synthesize(answer_part)
                        if audio:
                            from src.audio.player import AudioPlayer
                            player = AudioPlayer(sample_rate=24000)
                            await player.play_bytes(audio)
                except Exception:
                    logger.exception("TTS playback failed (non-fatal)")
