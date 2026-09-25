"""Forecast routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from forecast_forge.api.dependencies import get_orchestrator
from forecast_forge.api.errors import APIException
from forecast_forge.api.schemas import (
    ForecastPointAPI,
    ForecastResponse,
    GridResponse,
    LocationAPI,
    ProviderResultAPI,
)
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.orchestrator.service import ForecastOrchestrator
from forecast_forge.spatial.grid_service import build_spatial_grid

router = APIRouter()


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    name: str = Query("Unknown", max_length=100),
    horizon_hours: int = Query(72, ge=1, le=240),
    orchestrator: ForecastOrchestrator = Depends(get_orchestrator),
):
    """Fetch raw forecasts from all configured providers."""
    loc = Location(name=name, latitude=latitude, longitude=longitude)
    req = ForecastRequest(
        location=loc,
        variables=["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
        forecast_days=(horizon_hours // 24) or 1,
    )

    try:
        results = await orchestrator.fetch_all(req)
    except Exception as e:
        raise APIException("FORECAST_ERROR", str(e), status_code=500) from e

    provider_apis = {}
    for model_name, res in results.items():
        records_api = []
        for r in res.records:
            records_api.append(
                ForecastPointAPI(
                    timestamp=r.timestamp,
                    temperature_2m=r.temperature_2m,
                    relative_humidity_2m=r.relative_humidity_2m,
                    precipitation=r.precipitation,
                    wind_speed_10m=r.wind_speed_10m,
                )
            )

        provider_apis[model_name] = ProviderResultAPI(
            model=model_name,
            status=res.status.name if hasattr(res, "status") else "UNKNOWN",
            records=records_api,
        )

    return ForecastResponse(
        location=LocationAPI(name=name, latitude=latitude, longitude=longitude),
        retrieval_timestamp=datetime.now(UTC),
        providers=provider_apis,
    )


@router.get("/forecast/grid", response_model=GridResponse)
async def get_forecast_grid(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variable: str = Query("temperature_2m"),
    model: str = Query("ecmwf_ifs025"),
    valid_time: str | None = Query(None),
    grid_size: int = Query(5, ge=3, le=9),
    step: float = Query(0.25, ge=0.1, le=1.0),
):
    """Fetch spatial meteorological grid for real weather model overlays."""
    try:
        return await build_spatial_grid(
            center_lat=latitude,
            center_lon=longitude,
            variable=variable,
            model=model,
            valid_time=valid_time,
            grid_size=grid_size,
            step=step,
        )
    except Exception as e:
        raise APIException("GRID_ERROR", str(e), status_code=500) from e
