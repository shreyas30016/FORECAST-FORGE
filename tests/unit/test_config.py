"""Unit tests for configuration management."""

import pytest
from pydantic import ValidationError

from forecast_forge.config import Settings, get_settings


def test_default_settings():
    """Verify that default settings load with expected baseline values."""
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.open_meteo_base_url == "https://api.open-meteo.com/v1"
    assert settings.http_timeout_seconds == 10.0
    assert settings.http_max_retries == 3
    assert settings.http_backoff_factor == 0.5


def test_custom_settings():
    """Verify that settings accept valid custom overrides."""
    custom = Settings(
        app_env="production",
        log_level="WARNING",
        http_timeout_seconds=25.0,
        http_max_retries=5,
        http_backoff_factor=1.0,
    )
    assert custom.app_env == "production"
    assert custom.log_level == "WARNING"
    assert custom.http_timeout_seconds == 25.0
    assert custom.http_max_retries == 5
    assert custom.http_backoff_factor == 1.0


def test_invalid_settings():
    """Verify that invalid field constraints raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        Settings(http_timeout_seconds=-1.0)

    with pytest.raises(ValidationError):
        Settings(http_max_retries=-1)


def test_get_settings_cached():
    """Verify that get_settings returns a cached singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
