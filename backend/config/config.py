"""
J.A.R.V.I.S Configuration Manager
Centralized configuration with .env loading, validation, and typed getters.
Works alongside settings.py (pydantic-settings) for backward compatibility.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Any

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"


class ConfigError(Exception):
    """Raised when a required configuration value is missing or invalid."""
    pass


class Config:
    """
    Centralized configuration manager.
    Loads from .env file and environment variables.
    Provides typed getters with defaults and validation.
    """

    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not Config._loaded:
            self._values = {}
            self._load_env()
            Config._loaded = True

    def _load_env(self):
        """Load all values from .env file at startup."""
        try:
            from dotenv import load_dotenv
            if ENV_FILE.exists():
                load_dotenv(ENV_FILE, override=True)
            else:
                print(f"[CONFIG] WARNING: .env file not found at {ENV_FILE}")
        except ImportError:
            print("[CONFIG] WARNING: python-dotenv not installed, using system env only")

        # Cache all relevant env vars
        for key in os.environ:
            self._values[key] = os.environ[key]

    def reload(self):
        """Reload configuration from .env file."""
        Config._loaded = False
        self._values = {}
        self._load_env()
        Config._loaded = True

    # ── Typed Getters ─────────────────────────────────────────────────

    def get_str(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a string configuration value."""
        val = os.environ.get(key, self._values.get(key, default))
        if val is None:
            return default
        val = str(val).strip()
        # Reject placeholder values
        placeholders = ["your_key_here", "your-key-here", "changeme", "xxx", "TODO"]
        if val.lower() in [p.lower() for p in placeholders]:
            return default
        return val if val else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        val = self.get_str(key)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float configuration value."""
        val = self.get_str(key)
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        val = self.get_str(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes", "on")

    def get_list(self, key: str, separator: str = ",", default: list = None) -> list:
        """Get a list configuration value (comma-separated)."""
        val = self.get_str(key)
        if val is None:
            return default or []
        return [item.strip() for item in val.split(separator) if item.strip()]

    # ── Required Keys ─────────────────────────────────────────────────

    REQUIRED_KEYS = [
        "BACKEND_PORT",
    ]

    OPTIONAL_KEYS_WITH_DEFAULTS = {
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "BACKEND_PORT": "8765",
        "WS_PORT": "8765",
        "WAKE_WORD": "jarvis",
        "LOG_LEVEL": "INFO",
        "FRONTEND_URL": "http://localhost:5173",
        "USER_NAME": "Hari",
        "TTS_PROVIDER": "edge",
        "DEFAULT_AI_PROVIDER": "gemini",
        "DEFAULT_AI_MODEL": "gemini-1.5-flash",
        "WHISPER_MODEL": "base",
        "HOST": "127.0.0.1",
        "PORT": "8765",
        "DEBUG": "true",
    }

    def validate(self) -> dict:
        """
        Validate configuration and return status report.
        Returns: {"valid": bool, "errors": list, "warnings": list}
        """
        errors = []
        warnings = []

        # Check if .env exists
        if not ENV_FILE.exists():
            errors.append(f".env file not found at {ENV_FILE}")

        # Check for at least one AI provider key
        has_ai_key = False
        for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
            val = self.get_str(key)
            if val:
                has_ai_key = True
                break

        if not has_ai_key:
            warnings.append(
                "No AI provider API key configured (OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY). "
                "Only local models (Ollama) will be available."
            )

        # Check required keys
        port = self.get_str("PORT", self.get_str("BACKEND_PORT", "8765"))
        if not port:
            errors.append("PORT/BACKEND_PORT not configured")

        # Check wake word
        wake = self.get_str("WAKE_WORD", "jarvis")
        if not wake:
            warnings.append("WAKE_WORD not set, defaulting to 'jarvis'")

        # Check user name
        user = self.get_str("USER_NAME", "Hari")
        if not user:
            warnings.append("USER_NAME not set, defaulting to 'Hari'")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_or_exit(self):
        """Validate config and exit with clear error if critical keys missing."""
        result = self.validate()
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"⚠️  CONFIG WARNING: {w}")
        if not result["valid"]:
            for e in result["errors"]:
                print(f"❌ CONFIG ERROR: {e}")
            print("\nPlease fix the above errors in your .env file and try again.")
            sys.exit(1)

    # ── Convenience Properties ────────────────────────────────────────

    @property
    def OPENAI_API_KEY(self) -> Optional[str]:
        return self.get_str("OPENAI_API_KEY")

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        return self.get_str("GEMINI_API_KEY")

    @property
    def ANTHROPIC_API_KEY(self) -> Optional[str]:
        return self.get_str("ANTHROPIC_API_KEY")

    @property
    def PORT(self) -> int:
        return self.get_int("PORT", 8765)

    @property
    def HOST(self) -> str:
        return self.get_str("HOST", "127.0.0.1")

    @property
    def DEBUG(self) -> bool:
        return self.get_bool("DEBUG", True)

    @property
    def USER_NAME(self) -> str:
        return self.get_str("USER_NAME", "Hari")

    @property
    def WAKE_WORD(self) -> str:
        return self.get_str("WAKE_WORD", "jarvis")

    @property
    def LOG_LEVEL(self) -> str:
        return self.get_str("LOG_LEVEL", "INFO")

    @property
    def TTS_PROVIDER(self) -> str:
        return self.get_str("TTS_PROVIDER", "edge")

    @property
    def DEFAULT_AI_PROVIDER(self) -> str:
        return self.get_str("DEFAULT_AI_PROVIDER", "gemini")

    @property
    def DEFAULT_AI_MODEL(self) -> str:
        return self.get_str("DEFAULT_AI_MODEL", "gemini-1.5-flash")

    @property
    def WHISPER_MODEL(self) -> str:
        return self.get_str("WHISPER_MODEL", "base")

    @property
    def FRONTEND_URL(self) -> str:
        return self.get_str("FRONTEND_URL", "http://localhost:5173")


# Singleton instance
config = Config()
