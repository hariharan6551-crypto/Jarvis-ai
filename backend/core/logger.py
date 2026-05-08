"""
J.A.R.V.I.S Logging System
Structured logging with file rotation, console output, and module tagging.
RotatingFileHandler → backend/logs/jarvis.log
Max 10MB per file, keep last 5.
Format: [2026-05-08 14:32:01] [MODULE] [LEVEL] message
All modules import and use this shared logger.
Errors include full stack trace + module name.
"""

import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Remove default handler
logger.remove()

# ── Console handler with color ────────────────────────────────────────
logger.add(
    sys.stdout,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan> | "
        "<level>{message}</level>"
    ),
    level="INFO",
    colorize=True,
    filter=lambda record: record["extra"].get("name", "root") is not None,
    backtrace=True,
    diagnose=True,
)

# ── Main log file with rotation (10MB, keep 5) ────────────────────────
logger.add(
    str(LOG_DIR / "jarvis.log"),
    format=(
        "[{time:YYYY-MM-DD HH:mm:ss}] "
        "[{extra[name]}] "
        "[{level}] "
        "{message}"
    ),
    level="DEBUG",
    rotation="10 MB",
    retention=5,
    compression="zip",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
    enqueue=True,  # Thread-safe logging
)

# ── Date-based log file (backward compat) ─────────────────────────────
logger.add(
    str(LOG_DIR / "jarvis_{time:YYYY-MM-DD}.log"),
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{extra[name]}:{function}:{line} - {message}"
    ),
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
    enqueue=True,
)

# ── Error-only log file ───────────────────────────────────────────────
logger.add(
    str(LOG_DIR / "errors_{time:YYYY-MM-DD}.log"),
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{extra[name]}:{function}:{line} - {message}"
    ),
    level="ERROR",
    rotation="5 MB",
    retention="30 days",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
    enqueue=True,
)


def get_logger(name: str = "jarvis"):
    """
    Get a named logger instance.
    Usage:
        from core.logger import get_logger
        log = get_logger("voice")
        log.info("Voice engine started")
        log.error("Failed to init mic")
    """
    return logger.bind(name=name)
