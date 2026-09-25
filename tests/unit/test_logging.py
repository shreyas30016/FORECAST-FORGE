"""Unit tests for logging configuration."""

import logging

from forecast_forge.logging_config import configure_logging, get_logger


def test_configure_logging():
    """Verify configure_logging applies the requested level and configures handlers."""
    configure_logging(log_level="DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) >= 1

    # Re-apply with INFO
    configure_logging(log_level="INFO")
    assert root_logger.level == logging.INFO


def test_get_logger():
    """Verify get_logger returns a Logger instance with the expected name."""
    logger = get_logger("forecast_forge.test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "forecast_forge.test"
