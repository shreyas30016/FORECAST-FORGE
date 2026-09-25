"""Orchestration service for concurrent multi-model weather forecast retrieval."""

import asyncio

from forecast_forge.config import Settings, get_settings
from forecast_forge.core.models import ForecastRequest, HistoricalRequest, ProviderResult
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.base import BaseWeatherProvider
from forecast_forge.providers.open_meteo.aifs import ECMWFAIFSProvider
from forecast_forge.providers.open_meteo.gfs import NOAAGFSProvider
from forecast_forge.providers.open_meteo.ifs import ECMWFIFSProvider

logger = get_logger(__name__)


class ForecastOrchestrator:
    """Orchestrates concurrent queries to multiple numerical weather prediction providers."""

    def __init__(
        self,
        providers: list[BaseWeatherProvider] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.providers = (
            providers
            if providers is not None
            else [
                ECMWFIFSProvider(self.settings),
                NOAAGFSProvider(self.settings),
                ECMWFAIFSProvider(self.settings),
            ]
        )

    async def fetch_all(self, request: ForecastRequest) -> dict[str, ProviderResult]:
        """Fetch forecasts from all configured providers concurrently.

        Fault isolation: If any provider fails or returns invalid/null data,
        the remaining providers still complete successfully.
        """
        logger.info(
            "Orchestrator requesting (lat=%.4f, lon=%.4f) across %d providers",
            request.location.latitude,
            request.location.longitude,
            len(self.providers),
        )

        tasks = [provider.fetch_forecast(request) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        aggregated: dict[str, ProviderResult] = {}

        for provider, res in zip(self.providers, results, strict=True):
            if isinstance(res, ProviderResult):
                aggregated[provider.model_name] = res
            else:
                # Catastrophic unhandled exception fallback
                logger.error(
                    "Unhandled exception executing provider %s (%s): %s",
                    provider.provider_name,
                    provider.model_name,
                    str(res),
                )
        return aggregated

    async def fetch_historical_all(self, request: "HistoricalRequest") -> dict[str, ProviderResult]:
        """Fetch historical forecasts from all configured providers concurrently.

        Fault isolation: If any provider fails or returns invalid/null data,
        the remaining providers still complete successfully.
        """
        logger.info(
            "Orchestrator requesting historical data (lat=%.4f, lon=%.4f) across %d providers",
            request.location.latitude,
            request.location.longitude,
            len(self.providers),
        )

        tasks = [provider.fetch_historical(request) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        aggregated: dict[str, ProviderResult] = {}

        for provider, res in zip(self.providers, results, strict=True):
            if isinstance(res, ProviderResult):
                aggregated[provider.model_name] = res
            else:
                logger.error(
                    "Unhandled exception executing historical provider %s (%s): %s",
                    provider.provider_name,
                    provider.model_name,
                    str(res),
                )
        return aggregated
