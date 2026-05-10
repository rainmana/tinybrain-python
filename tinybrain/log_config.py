"""Logging configuration using Loguru."""

import sys
from pathlib import Path

from loguru import logger

from tinybrain.config import settings


def setup_logging(mcp_mode: bool = False) -> None:
    """Configure Loguru logging."""
    # Remove default handler
    logger.remove()

    # Only add console handler if not in MCP mode (MCP uses stdio)
    if not mcp_mode:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
        )

    # File handler with rotation (always enabled)
    if settings.log_file:
        log_file = Path(settings.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_file),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="zip",
            enqueue=True,
        )

    if not mcp_mode:
        logger.info("Logging configured")
