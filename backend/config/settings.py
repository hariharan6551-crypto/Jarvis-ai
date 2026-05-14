"""
J.A.R.V.I.S Configuration Settings
Central configuration management with environment variable support.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "J.A.R.V.I.S"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    LOG_LEVEL: str = "INFO"

    # Browser Automation
    CHROME_PROFILE_AUTO_DETECT: bool = True
    PLAYWRIGHT_HEADLESS: bool = False
    DEFAULT_BROWSER: str = "chrome"

    # Vision & OCR
    TESSERACT_PATH: Optional[str] = None
    OCR_LANGUAGE: str = "eng"
    VISION_CONFIDENCE_THRESHOLD: float = 60.0

    # Task Planner
    USE_AI_PLANNER: bool = True
    MAX_PLAN_STEPS: int = 10

    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_HOST: str = "http://localhost:11434"
    DEFAULT_AI_PROVIDER: str = "gemini"
    DEFAULT_AI_MODEL: str = "gemini-1.5-flash"

    # Weather
    OPENWEATHER_API_KEY: Optional[str] = None

    # Voice
    WHISPER_MODEL: str = "base"
    TTS_PROVIDER: str = "edge"  # edge, elevenlabs, pyttsx3
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"  # Adam
    EDGE_TTS_VOICE: str = "en-US-GuyNeural"
    WAKE_WORD: str = "jarvis"

    # Memory
    SQLITE_DB_PATH: str = str(BASE_DIR / "data" / "jarvis.db")
    CHROMA_DB_PATH: str = str(BASE_DIR / "data" / "chroma")

    # Security
    MAX_COMMAND_RETRIES: int = 3
    COMMAND_TIMEOUT: int = 30
    RESTRICTED_COMMANDS: list = [
        "format",
        "del /f",
        "rm -rf",
        "diskpart",
        "reg delete",
    ]

    # Audio
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024
    SILENCE_THRESHOLD: float = 0.01
    SILENCE_DURATION: float = 1.5

    # User
    USER_NAME: str = "Hari"

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Ensure data directories exist
os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
os.makedirs(BASE_DIR / "logs", exist_ok=True)
