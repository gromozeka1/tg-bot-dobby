from __future__ import annotations

import logging
import sys

from loguru import logger

from dobby.config import get_settings


class InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - glue code
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    logger.add(
        settings.logs_dir / "dobby.log",
        level=settings.log_level.upper(),
        rotation="10 MB",
        retention=14,
        encoding="utf-8",
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} | {message}",
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy in ("aiogram.event", "apscheduler", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
