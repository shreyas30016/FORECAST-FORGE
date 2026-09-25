"""Scientific Forecast Replay API routes."""

from datetime import datetime

from fastapi import APIRouter, Query

from forecast_forge.api.errors import APIException
from forecast_forge.replay.schemas import ReplayTimelineResponse
from forecast_forge.replay.service import ReplayService

router = APIRouter()
replay_service = ReplayService()


@router.get("/replay/timeline", response_model=ReplayTimelineResponse)
async def get_replay_timeline(
    run: datetime = Query(..., description="Exact initialization time of the model run (ISO 8601)"),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variable: str = Query("temperature_2m"),
):
    """Fetch the immutable causal replay sequence for a historical forecast."""
    try:
        from datetime import UTC

        if run.tzinfo is None:
            run = run.replace(tzinfo=UTC)
        return await replay_service.get_replay_timeline(
            latitude=latitude, longitude=longitude, run_time=run, variable=variable
        )
    except Exception as e:
        raise APIException("REPLAY_ERROR", str(e), status_code=500) from e
