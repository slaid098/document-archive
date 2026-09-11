"""App configuration: settings and logging setup."""

from app.config.logging_setup import setup_logging
from app.config.settings import Settings, settings

__all__ = ["Settings", "settings", "setup_logging"]
