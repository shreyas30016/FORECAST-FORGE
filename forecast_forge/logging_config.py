"""Structured logging configuration for Forecast Forge AI."""

import logging
import sys

from forecast_forge.config import get_settings

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(log_level: str | None = None) -> None:
    """Configure the root logger with standard formatting and handlers.

    Args:
        log_level: Optional override for logging level. If None, falls back
            to configured Settings.log_level.
    """
    level_name = log_level or get_settings().log_level
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance configured for the given module name."""
    return logging.getLogger(name)
