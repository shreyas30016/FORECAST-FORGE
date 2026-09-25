"""Extreme Weather Guidance routes."""

from fastapi import APIRouter, Query

from forecast_forge.api.errors import APIException
from forecast_forge.extremes.schemas import EventGuidance
from forecast_forge.extremes.service import ExtremesService

router = APIRouter()
extremes_service = ExtremesService()


@router.get("/extremes/guidance", response_model=list[EventGuidance])
async def get_extreme_weather_guidance(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    location_name: str = Query("Unknown"),
    lead_time_hours: int = Query(72),
    model: str = Query("gfs_seamless"),
):
    """Get Extreme Weather Guidance probabilities and context."""
    try:
        return await extremes_service.get_guidance(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            lead_time_hours=lead_time_hours,
            model=model,
        )
    except Exception as e:
        raise APIException("EXTREMES_ERROR", str(e), status_code=500) from e
