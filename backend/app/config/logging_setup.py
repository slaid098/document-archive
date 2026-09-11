"""Logging setup: a single loguru sink; stdlib records (tortoise, uvicorn) are intercepted."""

import inspect
import logging
import sys

from loguru import logger

from app.config.settings import settings


class InterceptHandler(logging.Handler):
    """Forward stdlib logging records into loguru, preserving location info."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """One sink for the whole app; log events carry context via logger.bind().

    The level comes from LOG_LEVEL in the environment; an unknown level
    fails fast at startup.
    """
    level = settings.log_level.upper()
    logger.remove()
    logger.add(sys.stdout, level=level)
    logging.basicConfig(handlers=[InterceptHandler()], level=level, force=True)
