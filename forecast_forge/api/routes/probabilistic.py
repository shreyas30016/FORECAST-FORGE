"""Probabilistic forecast routes."""

from fastapi import APIRouter, Query

from forecast_forge.api.errors import APIException
from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.ensemble.schemas import (
    EventProbabilityRequest,
    EventProbabilityResult,
    ProbabilisticForecast,
)
from forecast_forge.providers.open_meteo.ensemble import OpenMeteoEnsembleAdapter

router = APIRouter()


class ProbabilisticResponse(ProbabilisticForecast):
    """API response schema for probabilistic forecast."""

    pass


@router.get("/probabilistic/forecast", response_model=list[ProbabilisticResponse])
async def get_probabilistic_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variable: str = Query("temperature_2m"),
    horizon_hours: int = Query(72),
    model: str = Query("gfs_seamless"),
):
    """Get ensemble-member probabilistic forecast distributions."""

    # Map API model to member prefix
    if model == "gfs_seamless" or model == "gfs_ensemble":
        api_model = "gfs_seamless"
        prefix = "ncep_gefs_seamless"
    elif model == "icon_seamless" or model == "icon_ensemble":
        api_model = "icon_seamless"
        prefix = "icon_seamless_eps"
    elif model == "ecmwf_ifs04_ensemble" or model == "ecmwf_ensemble":
        raise APIException(
            "UNSUPPORTED_MODEL",
            "Open-Meteo ensemble API does not currently support "
            "ECMWF ensemble members for this tier.",
            status_code=400,
        )
    else:
        # Default to GFS if unknown
        api_model = "gfs_seamless"
        prefix = "ncep_gefs_seamless"

    adapter = OpenMeteoEnsembleAdapter(model_name=api_model, member_prefix=prefix)

    try:
        var_enum = WeatherVariable(variable)
    except ValueError:
        raise APIException("INVALID_VARIABLE", f"Variable {variable} is not supported.") from None

    loc = Location(name="Unknown", latitude=latitude, longitude=longitude)
    req = ForecastRequest(
        location=loc, variables=[var_enum], forecast_days=(horizon_hours // 24) or 1
    )

    try:
        results = await adapter.fetch_probabilistic_forecast(req)
    except Exception as e:
        raise APIException("ENSEMBLE_FETCH_ERROR", str(e), status_code=500) from e

    if var_enum not in results or not results[var_enum]:
        raise APIException("NO_DATA", "No probabilistic data available.", status_code=404)

    # Return just the probabilistic forecasts (first element of tuple)
    response_list = [prob for prob, _events in results[var_enum]]
    return response_list


@router.get("/probabilistic/probability", response_model=list[EventProbabilityResult])
async def get_event_probability(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variable: str = Query("precipitation"),
    operator: str = Query(">="),
    threshold: float = Query(1.0),
    horizon_hours: int = Query(72),
    model: str = Query("gfs_seamless"),
):
    """Get empirical event probabilities from ensemble members."""

    if model == "gfs_seamless" or model == "gfs_ensemble":
        api_model = "gfs_seamless"
        prefix = "ncep_gefs_seamless"
    elif model == "icon_seamless" or model == "icon_ensemble":
        api_model = "icon_seamless"
        prefix = "icon_seamless_eps"
    else:
        api_model = "gfs_seamless"
        prefix = "ncep_gefs_seamless"

    adapter = OpenMeteoEnsembleAdapter(model_name=api_model, member_prefix=prefix)

    try:
        var_enum = WeatherVariable(variable)
    except ValueError:
        raise APIException("INVALID_VARIABLE", f"Variable {variable} is not supported.") from None

    loc = Location(name="Unknown", latitude=latitude, longitude=longitude)
    req = ForecastRequest(
        location=loc, variables=[var_enum], forecast_days=(horizon_hours // 24) or 1
    )

    event_req = EventProbabilityRequest(variable=variable, operator=operator, threshold=threshold)

    try:
        results = await adapter.fetch_probabilistic_forecast(req, [event_req])
    except Exception as e:
        raise APIException("ENSEMBLE_FETCH_ERROR", str(e), status_code=500) from e

    if var_enum not in results or not results[var_enum]:
        raise APIException("NO_DATA", "No probabilistic data available.", status_code=404)

    response_list = []
    for _prob, events in results[var_enum]:
        if events:
            response_list.extend(events)

    return response_list
