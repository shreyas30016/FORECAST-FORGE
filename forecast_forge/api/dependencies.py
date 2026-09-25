"""FastAPI dependencies."""

from forecast_forge.config import Settings, get_settings
from forecast_forge.orchestrator.service import ForecastOrchestrator

# Global instances for the app lifecycle
_settings = get_settings()
_orchestrator = ForecastOrchestrator(settings=_settings)


def get_api_settings() -> Settings:
    """Dependency for application settings."""
    return _settings


def get_orchestrator() -> ForecastOrchestrator:
    """Dependency for the forecast orchestrator."""
    return _orchestrator
