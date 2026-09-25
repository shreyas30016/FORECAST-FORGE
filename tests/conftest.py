"""Pytest fixtures and configuration."""

import pytest

from forecast_forge.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test to ensure test isolation."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def default_settings() -> Settings:
    """Return a fresh default Settings instance."""
    return Settings()
