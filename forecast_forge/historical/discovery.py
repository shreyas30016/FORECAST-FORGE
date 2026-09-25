"""Availability discovery for historical forecast data."""

import asyncio
from datetime import date

from forecast_forge.config import get_settings
from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.models import HistoricalRequest, Location
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.base import BaseWeatherProvider
from forecast_forge.providers.open_meteo.aifs import ECMWFAIFSProvider
from forecast_forge.providers.open_meteo.gfs import NOAAGFSProvider
from forecast_forge.providers.open_meteo.ifs import ECMWFIFSProvider

logger = get_logger(__name__)


async def discover_historical_availability(
    location: Location,
    start_date: date,
    end_date: date,
    providers: list[BaseWeatherProvider] | None = None,
) -> dict[str, ProviderStatus]:
    """
    Check which providers have valid historical data for the given period.
    This does a lightweight fetch (just temperature) to verify actual data presence,
    preventing issues like AIFS returning HTTP 200 but all nulls.
    """
    settings = get_settings()
    providers = providers or [
        ECMWFIFSProvider(settings),
        NOAAGFSProvider(settings),
        ECMWFAIFSProvider(settings),
    ]

    # We only request temperature for discovery to minimize payload size
    request = HistoricalRequest(
        location=location,
        start_date=start_date,
        end_date=end_date,
        variables=[WeatherVariable.TEMPERATURE_2M],
    )

    logger.info(
        "Discovering historical data availability for %s to %s across %d providers",
        start_date,
        end_date,
        len(providers),
    )

    tasks = [provider.fetch_historical(request) for provider in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    availability: dict[str, ProviderStatus] = {}
    for provider, res in zip(providers, results, strict=True):
        if isinstance(res, Exception):
            logger.error("Discovery error for %s: %s", provider.model_name, res)
            availability[provider.model_name] = ProviderStatus.ERROR
        else:
            logger.info(
                "Discovery result for %s: %s (Valid records: %d/%d)",
                provider.model_name,
                res.status.value,
                res.valid_records,
                res.total_records,
            )
            availability[provider.model_name] = res.status

    return availability
