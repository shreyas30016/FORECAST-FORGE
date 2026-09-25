"""API router for Decision Trace endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.trace.schemas import DecisionTrace
from forecast_forge.trace.storage import TraceStorage

router = APIRouter(prefix="/api/v1/decision-trace", tags=["trace"])
storage = TraceStorage()


@router.get("", response_model=list[DecisionTrace] | DecisionTrace)
async def get_decision_trace(
    trace_id: str | None = Query(None, description="Unique trace ID"),
    replay_id: str | None = Query(None, description="Unique replay ID"),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    valid_time: datetime | None = Query(None),
    lead_time_hours: int | None = Query(None),
    variable: str | None = Query(None),
):
    """Retrieve DecisionTrace by trace_id, replay_id, or forecast context."""
    if trace_id:
        trace = storage.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace

    if replay_id:
        traces = storage.find_by_replay(replay_id)
        if not traces:
            raise HTTPException(status_code=404, detail="No traces found for replay_id")
        return traces

    if all(x is not None for x in (latitude, longitude, valid_time, lead_time_hours, variable)):
        try:
            var_enum = WeatherVariable(variable)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid variable") from None

        trace = storage.find_trace(latitude, longitude, valid_time, lead_time_hours, var_enum)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found for given context")
        return trace

    raise HTTPException(
        status_code=400,
        detail="Must provide trace_id, replay_id, or full context (lat, lon, time, lead, var)",
    )
