#!/usr/bin/env python3
"""Voice Interview Assistant — main entry point."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from src.config import get_settings, setup_logging


def build_agent():
    """Build the interview agent with all dependencies."""
    settings = get_settings()

    # Load knowledge base
    from src.knowledge.loader import load_knowledge
    from src.knowledge.retriever import KnowledgeRetriever

    chunks = load_knowledge(settings.knowledge_dir, settings.chunk_max_tokens)
    if not chunks:
        logging.warning("No knowledge chunks loaded — agent will have no context")
    retriever = KnowledgeRetriever(chunks)

    # Initialize LLM
    from src.llm.openai_client import OpenAILLMClient

    if not settings.llm_api_key:
        print("⚠️  LLM_API_KEY not set. Set it in .env or environment.")
        print("   Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    llm = OpenAILLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )

    # Build agent
    from src.agent.agent import InterviewAgent

    agent = InterviewAgent(
        llm=llm,
        retriever=retriever,
        person_name=settings.person_name,
        max_chunks=settings.max_chunks,
    )

    return agent, settings


def build_tts(settings):
    """Build TTS client based on configuration."""
    if settings.elevenlabs_api_key:
        from src.tts.elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model_id,
        )
    else:
        logging.warning("ELEVENLABS_API_KEY not set, using DummyTTS")
        from src.tts.elevenlabs_tts import DummyTTS
        return DummyTTS()


def build_stt(settings):
    """Build STT client based on configuration."""
    if settings.stt_provider == "deepgram" and settings.deepgram_api_key:
        from src.stt.deepgram_stt import DeepgramSTT
        return DeepgramSTT(
            api_key=settings.deepgram_api_key,
            sample_rate=settings.sample_rate,
        )
    else:
        try:
            from src.stt.whisper_stt import WhisperSTT
            return WhisperSTT(model_size=settings.whisper_model)
        except Exception as e:
            logging.warning("Whisper not available: %s", e)
            from src.stt.whisper_stt import DummySTT
            return DummySTT()


async def run_voice(args):
    """Run in voice mode: mic -> STT -> agent -> TTS -> speakers."""
    agent, settings = build_agent()
    tts = build_tts(settings)
    stt = build_stt(settings)

    from src.audio.vad import EnergyVAD
    from src.loop import VoiceLoop
    from src.transport.local import LocalAudioTransport

    transport = LocalAudioTransport(
        sample_rate=settings.sample_rate,
        frame_duration_ms=settings.frame_duration_ms,
    )
    vad = EnergyVAD(
        threshold=settings.vad_threshold,
        silence_duration_ms=settings.vad_silence_duration_ms,
        sample_rate=settings.sample_rate,
        frame_duration_ms=settings.frame_duration_ms,
    )

    loop = VoiceLoop(
        agent=agent,
        stt=stt,
        tts=tts,
        transport=transport,
        vad=vad,
    )
    await loop.run()


async def run_text(args):
    """Run in text mode: stdin -> agent -> stdout (+ optional TTS)."""
    agent, settings = build_agent()
    tts = build_tts(settings) if not args.no_tts else None

    from src.loop import TextLoop

    loop = TextLoop(agent=agent, tts=tts)
    await loop.run()


async def run_web(args):
    """Run web server with WebSocket interface."""
    agent, settings = build_agent()
    tts = build_tts(settings)

    import uvicorn
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    import os

    app = FastAPI(title="Voice Interview Assistant")

    web_dir = os.path.join(os.path.dirname(__file__), "web")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(web_dir, "index.html"))

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = await ws.receive_text()
                # Text mode over WebSocket
                response_parts: list[str] = []
                async for token in agent.respond_stream(data):
                    response_parts.append(token)
                    await ws.send_json({"type": "token", "text": token})
                await ws.send_json({"type": "done", "text": "".join(response_parts)})
        except WebSocketDisconnect:
            logging.info("WebSocket client disconnected")

    print(f"\n🌐 Web interface: http://localhost:{settings.web_port}\n")
    config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def main():
    parser = argparse.ArgumentParser(
        description="Voice Interview Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  voice   Real-time voice mode (mic + speakers)
  text    Text-only mode (stdin/stdout)
  web     Web interface with WebSocket

Examples:
  python main.py --mode text
  python main.py --mode voice
  python main.py --mode web --port 8080
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["voice", "text", "web"],
        default="text",
        help="Interaction mode (default: text)",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable TTS playback in text mode",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Web server port (overrides WEB_PORT env var)",
    )

    args = parser.parse_args()
    setup_logging()

    if args.port:
        import os
        os.environ["WEB_PORT"] = str(args.port)

    if args.mode == "voice":
        asyncio.run(run_voice(args))
    elif args.mode == "text":
        asyncio.run(run_text(args))
    elif args.mode == "web":
        asyncio.run(run_web(args))


if __name__ == "__main__":
    main()
