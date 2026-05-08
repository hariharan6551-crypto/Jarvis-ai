"""
J.A.R.V.I.S Logging System
Structured logging with file rotation and console output.
"""

import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Remove default handler
logger.remove()

# Console handler with color
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# File handler with rotation
logger.add(
    str(LOG_DIR / "jarvis_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
)

# Error file handler
logger.add(
    str(LOG_DIR / "errors_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="5 MB",
    retention="30 days",
)


def get_logger(name: str):
    """Get a named logger instance."""
    return logger.bind(name=name)
