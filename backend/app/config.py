"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

WhisperSize = Literal["tiny", "base", "small", "medium", "large-v3-turbo"]

# The user-facing speed/accuracy choice maps to a Whisper model size.
MODEL_PRESETS: dict[str, WhisperSize] = {
    "fast": "base",
    "balanced": "small",
    "accurate": "large-v3-turbo",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SS_", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://smartspeaking:smartspeaking@localhost:5432/smartspeaking"
    )
    redis_url: str = "redis://localhost:6379/0"

    media_dir: Path = Path("./data/media")
    models_dir: Path = Path("./data/models")

    max_upload_bytes: int = 2 * 1024**3  # 2 GB
    max_duration_s: float = 15 * 60 + 30  # 15 min plus a little grace
    min_duration_s: float = 5.0

    default_preset: str = "balanced"
    whisper_device: Literal["auto", "cpu", "cuda"] = "auto"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    llm_enabled: bool = True

    job_timeout_s: int = 60 * 60

    cookie_secure: bool = False  # set true when served over HTTPS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
