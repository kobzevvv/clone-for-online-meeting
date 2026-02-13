from __future__ import annotations

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_turbo_v2_5"

    # LLM
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    # STT
    stt_provider: str = "whisper"
    deepgram_api_key: str = ""
    whisper_model: str = "base"

    # Knowledge
    knowledge_dir: str = "./knowledge"
    max_chunks: int = 5
    chunk_max_tokens: int = 300

    # Audio
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 30
    vad_threshold: float = 0.5
    vad_silence_duration_ms: int = 800

    # Server
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # Agent
    person_name: str = "Daniel"

    # Telegram
    telegram_bot_token: str = ""

    # Logging
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def setup_logging(level: str | None = None) -> None:
    lvl = level or get_settings().log_level
    logging.basicConfig(
        level=getattr(logging, lvl.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
