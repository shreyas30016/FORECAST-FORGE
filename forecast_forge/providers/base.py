"""Abstract base interface for numerical weather prediction providers."""

from abc import ABC, abstractmethod

from forecast_forge.core.enums import ProviderStatus
from forecast_forge.core.models import ForecastRequest, HistoricalRequest, ProviderResult


class BaseWeatherProvider(ABC):
    """Abstract interface for all weather prediction provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the descriptive name of the data source provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the numerical model identifier."""

    @abstractmethod
    async def fetch_forecast(self, request: ForecastRequest) -> ProviderResult:
        """Fetch and normalize weather forecast for the specified request.

        Args:
            request: ForecastRequest containing location coordinates and variables.

        Returns:
            ProviderResult containing normalized ForecastPoints and quality metadata.
        """

    @abstractmethod
    async def fetch_historical(self, request: HistoricalRequest) -> ProviderResult:
        """Fetch historical weather forecast for the specified request.

        Args:
            request: HistoricalRequest containing location and date range.

        Returns:
            ProviderResult containing normalized historical ForecastPoints.
        """

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Execute a lightweight health check to determine provider availability."""
