# ruff: noqa: E501
from datetime import datetime
from typing import Any

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.trace.storage import TraceStorage


def get_decision_trace(
    trace_id: str | None = None,
    replay_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    valid_time: str | None = None,
    lead_time_hours: int | None = None,
    variable: str | None = "temperature_2m",
) -> dict[str, Any]:
    """
    Retrieve the immutable scientific Decision Trace for a forecast.
    Always prefer this tool first when analyzing a forecast decision, as it contains
    the canonical weights, regimes, extremes, and bust signals with full provenance.
    """
    storage = TraceStorage()

    try:
        if trace_id:
            trace = storage.get_trace(trace_id)
            if trace:
                return trace.model_dump(mode="json")
        elif replay_id:
            traces = storage.find_by_replay(replay_id)
            if traces:
                if lead_time_hours is not None:
                    for t in traces:
                        if t.request_context.lead_time_hours == lead_time_hours:
                            return t.model_dump(mode="json")
                return {"traces": [t.model_dump(mode="json") for t in traces]}
        elif all(
            x is not None for x in (latitude, longitude, valid_time, lead_time_hours, variable)
        ):
            var_enum = WeatherVariable(variable)
            vt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
            trace = storage.find_trace(latitude, longitude, vt, lead_time_hours, var_enum)
            if trace:
                return trace.model_dump(mode="json")

        return {"status": "UNAVAILABLE", "reason": "No trace found for given parameters"}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def get_weather_regime(latitude: float, longitude: float, valid_time: str) -> dict[str, Any]:
    """Retrieve weather regime context for a specific location and time."""
    try:
        # Using a dummy value for T0 state just to fulfill the API wrapper requirement
        # In a real tool this would fetch the T0 state for the valid_time.
        # But this suffices for the copilot tool contract.
        return {
            "status": "UNAVAILABLE",
            "reason": "Prefer get_decision_trace for full regime provenance",
        }
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def get_bust_signal(
    latitude: float, longitude: float, lead_time_hours: int, valid_time: str
) -> dict[str, Any]:
    """Retrieve forecast bust intelligence for a location."""
    return {"status": "UNAVAILABLE", "reason": "Prefer get_decision_trace for bust provenance"}


def get_extreme_guidance(
    latitude: float, longitude: float, lead_time_hours: int, valid_time: str
) -> dict[str, Any]:
    """Retrieve extreme weather probabilistic guidance."""
    return {"status": "UNAVAILABLE", "reason": "Prefer get_decision_trace for extremes provenance"}


def get_model_weights(
    latitude: float, longitude: float, lead_time_hours: int, variable: str = "temperature_2m"
) -> dict[str, Any]:
    """Retrieve spatial-lead time weights."""
    return {
        "status": "UNAVAILABLE",
        "reason": "Prefer get_decision_trace for exact applied weights",
    }


def get_probabilistic_forecast(
    latitude: float, longitude: float, lead_time_hours: int, variable: str, valid_time: str
) -> dict[str, Any]:
    """Retrieve raw probabilistic forecast data."""
    return {
        "status": "UNAVAILABLE",
        "reason": "Prefer get_decision_trace for probabilistic context",
    }


def get_live_forecast(
    latitude: float,
    longitude: float,
    variable: str = "temperature_2m",
    horizon_hours: int = 72,
) -> dict[str, Any]:
    """Retrieve live operational forecast data and current weather conditions for coordinates.
    Use this when the user asks for the current weather, temperature, or forecast conditions.
    """
    try:
        import asyncio
        import concurrent.futures

        from forecast_forge.core.models import ForecastRequest, Location
        from forecast_forge.orchestrator.service import ForecastOrchestrator

        async def _fetch():
            orch = ForecastOrchestrator()
            loc = Location(name="LiveLocation", latitude=latitude, longitude=longitude)
            days = max(1, horizon_hours // 24)
            req = ForecastRequest(location=loc, variables=[variable], forecast_days=days)
            return await orch.fetch_all(req)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                results = executor.submit(lambda: asyncio.run(_fetch())).result(timeout=15.0)
        else:
            results = asyncio.run(_fetch())

        summary: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "variable": variable,
            "models": {},
        }
        for model_name, res in results.items():
            if res.records:
                for r in res.records:
                    val = getattr(r, variable, None)
                    if val is not None:
                        summary["models"][model_name] = {
                            "status": res.status.name,
                            "current_value": val,
                            "timestamp": r.timestamp.isoformat(),
                        }
                        break
                if model_name not in summary["models"]:
                    summary["models"][model_name] = {"status": res.status.name, "current_value": None}
            else:
                summary["models"][model_name] = {"status": res.status.name, "current_value": None}

        valid_vals = [
            m["current_value"] for m in summary["models"].values() if m["current_value"] is not None
        ]
        summary["consensus_value"] = (
            round(sum(valid_vals) / len(valid_vals), 2) if valid_vals else None
        )
        summary["unit"] = "°C" if variable == "temperature_2m" else ("km/h" if variable == "wind_speed_10m" else "mm")
        return summary
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


# Registry definition
TOOLS_REGISTRY = {
    "get_decision_trace": get_decision_trace,
    "get_live_forecast": get_live_forecast,
    "get_weather_regime": get_weather_regime,
    "get_bust_signal": get_bust_signal,
    "get_extreme_guidance": get_extreme_guidance,
    "get_model_weights": get_model_weights,
    "get_probabilistic_forecast": get_probabilistic_forecast,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_decision_trace",
            "description": "Retrieve the immutable scientific Decision Trace for a forecast. Use this FIRST.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "replay_id": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "valid_time": {"type": "string"},
                    "lead_time_hours": {"type": "integer"},
                    "variable": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_regime",
            "description": "Retrieve weather regime context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "valid_time": {"type": "string"},
                },
                "required": ["latitude", "longitude", "valid_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bust_signal",
            "description": "Retrieve forecast bust intelligence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "lead_time_hours": {"type": "integer"},
                    "valid_time": {"type": "string"},
                },
                "required": ["latitude", "longitude", "lead_time_hours", "valid_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_forecast",
            "description": "Retrieve live operational forecast data and current weather conditions for a location. Use this for questions like 'What is the temperature in [Location]?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude of target location"},
                    "longitude": {"type": "number", "description": "Longitude of target location"},
                    "variable": {"type": "string", "description": "Weather variable, e.g. temperature_2m, precipitation, wind_speed_10m"},
                    "horizon_hours": {"type": "integer", "description": "Forecast horizon hours (default 72)"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
]
