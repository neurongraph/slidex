"""
Central logging configuration using loguru.
All modules should import and use the logger from this file.
"""

import sys
from loguru import logger

from slidex.config import settings


# Remove default handler
logger.remove()

# Add console handler with formatting
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True,
)

# Add file handler for persistent logs
logger.add(
    settings.storage_root / "logs" / "slidex.log",
    rotation="10 MB",
    retention="1 week",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

logger.info("Logging initialized")
