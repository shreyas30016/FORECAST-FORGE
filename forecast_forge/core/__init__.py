"""Core domain interfaces, models, enums, and exceptions."""

from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.exceptions import (
    ForecastForgeError,
    ProviderError,
    ProviderHTTPError,
    ProviderMalformedDataError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ValidationError,
)
from forecast_forge.core.models import (
    ForecastPoint,
    ForecastRequest,
    Location,
    ProviderResult,
)

__all__ = [
    "ProviderStatus",
    "WeatherVariable",
    "ForecastForgeError",
    "ValidationError",
    "ProviderError",
    "ProviderHTTPError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderMalformedDataError",
    "Location",
    "ForecastRequest",
    "ForecastPoint",
    "ProviderResult",
]
