"""Forecast-Bust Intelligence routes."""

from fastapi import APIRouter, Query

from forecast_forge.api.errors import APIException
from forecast_forge.evaluation.bust.schemas import ForecastBustSignal
from forecast_forge.evaluation.bust.service import ForecastBustService

router = APIRouter()
bust_service = ForecastBustService()


@router.get("/bust/signal", response_model=ForecastBustSignal)
async def get_forecast_bust_signal(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    location_name: str = Query("Unknown"),
    lead_time_hours: int = Query(72),
    variable: str = Query("temperature_2m"),
    model: str = Query("gfs_seamless"),
):
    """Get Forecast-Bust Intelligence signal."""
    try:
        return await bust_service.get_bust_signal(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            lead_time_hours=lead_time_hours,
            variable=variable,
            model=model,
        )
    except Exception as e:
        raise APIException("BUST_ERROR", str(e), status_code=500) from e
