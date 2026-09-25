"""Orchestrates historical dataset extraction and assembly."""

import asyncio
from datetime import date, datetime
from typing import Any

import pandas as pd

from forecast_forge.core.models import HistoricalRequest, Location
from forecast_forge.historical.reference_data import ERA5ReferenceProvider
from forecast_forge.logging_config import get_logger
from forecast_forge.orchestrator.service import ForecastOrchestrator

logger = get_logger(__name__)


async def extract_historical_dataset(
    location: Location,
    start_date: date,
    end_date: date,
    run: datetime | None = None,
    lead_time_days: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract historical models and reference data for the period.

    Uses Previous Runs API as primary lead-time acquisition path (24h, 48h, ..., 168h)
    or Single Runs API when an explicit model initialization run is requested.
    Returns a tuple of (models_df, reference_df).
    """
    orchestrator = ForecastOrchestrator()

    if run is not None:
        logger.info(
            "Starting historical extraction for run %s (%s to %s)",
            run.isoformat(),
            start_date,
            end_date,
        )
        req = HistoricalRequest(
            location=location,
            start_date=start_date,
            end_date=end_date,
            run=run,
        )
    else:
        logger.info(
            "Starting historical lead-time extraction via Previous Runs API from %s to %s",
            start_date,
            end_date,
        )
        req = HistoricalRequest(
            location=location,
            start_date=start_date,
            end_date=end_date,
            lead_time_days=lead_time_days or [1, 2, 3, 4, 5, 6, 7],
        )

    # Fetch providers sequentially with gentle pacing to avoid bursting Open-Meteo rate limit
    model_results: dict[str, Any] = {}
    for provider in orchestrator.providers:
        res = await provider.fetch_historical(req)
        model_results[provider.model_name] = res
        await asyncio.sleep(0.4)

    model_results_list = [model_results]

    models_records = []
    for model_results in model_results_list:
        for model_name, res in model_results.items():
            if res.records:
                for pt in res.records:
                    models_records.append(
                        {
                            "model": model_name,
                            "valid_time": pt.timestamp.replace(
                                tzinfo=None
                            ),  # Pandas likes naive or explicit tz
                            "latitude": pt.latitude,
                            "longitude": pt.longitude,
                            "temperature_2m": pt.temperature_2m,
                            "relative_humidity_2m": pt.relative_humidity_2m,
                            "precipitation": pt.precipitation,
                            "wind_speed_10m": pt.wind_speed_10m,
                            "cloud_cover": pt.cloud_cover,
                            "lead_time_hours": pt.lead_time_hours,
                            "initialization_time": pt.initialization_time.replace(tzinfo=None)
                            if pt.initialization_time
                            else None,
                            "lead_time_semantics": pt.lead_time_semantics,
                            "provenance_source": pt.provenance_source,
                        }
                    )
            else:
                logger.warning(
                    "No records returned for %s (status: %s)", model_name, res.status.value
                )

    # Remove duplicates if overlapping entries exist
    models_df = pd.DataFrame(models_records)
    if not models_df.empty:
        models_df = models_df.drop_duplicates(subset=["model", "valid_time", "lead_time_hours"])

    # 2. Fetch Reference (ERA5 reanalysis reference benchmark)
    ref_request = HistoricalRequest(
        location=location,
        start_date=start_date,
        end_date=end_date,
    )
    ref_provider = ERA5ReferenceProvider()
    ref_res = await ref_provider.fetch_reference_data(ref_request)

    ref_records = []
    if ref_res.status.value in ("AVAILABLE", "PARTIAL"):
        for pt in ref_res.records:
            ref_records.append(
                {
                    "model": pt.model,
                    "valid_time": pt.timestamp.replace(tzinfo=None),
                    "latitude": pt.latitude,
                    "longitude": pt.longitude,
                    "ref_temperature_2m": pt.temperature_2m,
                    "ref_relative_humidity_2m": pt.relative_humidity_2m,
                    "ref_precipitation": pt.precipitation,
                    "ref_wind_speed_10m": pt.wind_speed_10m,
                    "ref_cloud_cover": pt.cloud_cover,
                }
            )

    ref_df = pd.DataFrame(ref_records)

    return models_df, ref_df
