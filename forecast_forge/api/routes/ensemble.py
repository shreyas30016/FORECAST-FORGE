"""Ensemble routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from forecast_forge.api.dependencies import get_orchestrator
from forecast_forge.api.errors import APIException
from forecast_forge.api.schemas import (
    EnsembleMetaAPI,
    EnsembleResponse,
    LocationAPI,
    ModelForecastAPI,
    RegimeWeightRecord,
    RegimeWeightResponse,
    SpatialLeadTimeWeightGridResponse,
    SpatialWeightGridResponse,
)
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.ensemble.engine import generate_ensemble_forecast
from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast
from forecast_forge.orchestrator.service import ForecastOrchestrator

router = APIRouter()


@router.get("/ensemble", response_model=EnsembleResponse)
async def get_ensemble(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    name: str = Query("Unknown"),
    horizon_hours: int = Query(72),
    variable: str = Query("temperature_2m"),
    orchestrator: ForecastOrchestrator = Depends(get_orchestrator),
):
    """Generate blended ensemble forecast."""
    loc = Location(name=name, latitude=latitude, longitude=longitude)
    req = ForecastRequest(
        location=loc, variables=[variable], forecast_days=(horizon_hours // 24) or 1
    )

    try:
        results = await orchestrator.fetch_all(req)
    except Exception as e:
        raise APIException("ENSEMBLE_FETCH_ERROR", str(e), status_code=500) from e

    # Calculate ensemble for the first valid future timestamp, or fallback to the latest
    # available record to provide the most immediately actionable point forecast.
    target_time = None
    now_utc = datetime.now(UTC)
    for _model_name, res in results.items():
        for r in res.records:
            if r.timestamp >= now_utc:
                target_time = r.timestamp
                break
        if target_time:
            break

    if not target_time:
        for _model_name, res in results.items():
            if res.records:
                target_time = max(r.timestamp for r in res.records)
                break

    if not target_time:
        raise APIException("NO_DATA", "No forecast data available from providers.", status_code=404)

    forecasts = []
    for model_name, res in results.items():
        record = next((r for r in res.records if r.timestamp == target_time), None)
        val = getattr(record, variable, None) if record else None

        if val is not None:
            forecasts.append(
                ModelForecast(model=model_name, value=val, is_valid=True, status="AVAILABLE")
            )
        else:
            # Null safety explicitly mapped
            forecasts.append(
                ModelForecast(
                    model=model_name, value=None, is_valid=False, status="NO_VALID_DATA"
                )
            )

    # Fallback historical weights used if dynamic adaptive weights cannot be calculated
    # for the requested coordinates/horizon. Derived from Phase 3 global performance metrics.
    fallback_weights = [
        EnsembleWeight(model="ecmwf_ifs025", weight=0.73),
        EnsembleWeight(model="gfs_seamless", weight=0.27),
    ]

    ensemble_res = generate_ensemble_forecast(
        location_name=name,
        variable=variable,
        valid_time=target_time.replace(tzinfo=None),
        forecasts=forecasts,
        historical_weights=fallback_weights,
        expected_total_models=3,
    )

    models_api = {}
    for mf in ensemble_res.model_forecasts:
        # Calculate effective weight
        w = 0.0
        if ensemble_res.adaptive_weights:
            w = next((w.weight for w in ensemble_res.adaptive_weights if w.model == mf.model), 0.0)
        elif fallback_weights and mf.is_valid:
            valid_models = {f.model for f in ensemble_res.model_forecasts if f.is_valid}
            total = sum(xw.weight for xw in fallback_weights if xw.model in valid_models)
            if total > 0:
                raw = next((xw.weight for xw in fallback_weights if xw.model == mf.model), 0.0)
                w = raw / total

        models_api[mf.model] = ModelForecastAPI(
            status=mf.status,
            forecast=mf.value,  # Will naturally serialize to null if None
            weight=w,
        )

    from forecast_forge.core.enums import WeatherVariable
    from forecast_forge.trace.storage import TraceStorage

    trace_id = None
    try:
        storage = TraceStorage()
        found_trace = storage.find_trace(
            latitude=latitude,
            longitude=longitude,
            valid_time=target_time.replace(tzinfo=None),
            lead_time_hours=horizon_hours,
            variable=WeatherVariable(variable)
        )
        if found_trace:
            trace_id = found_trace.trace_id
    except Exception:
        pass

    meta_api = EnsembleMetaAPI(
        forecast=ensemble_res.inverse_error_forecast,  # Fallback to Phase 3 weights
        method="INVERSE_ERROR",
        uncertainty=ensemble_res.uncertainty.spread,
        data_quality=ensemble_res.uncertainty.data_quality_indicator,
        trace_id=trace_id,
    )

    return EnsembleResponse(
        location=LocationAPI(name=name, latitude=latitude, longitude=longitude),
        retrieval_timestamp=datetime.now(UTC),
        valid_time=target_time,
        variable=variable,
        models=models_api,
        ensemble=meta_api,
        explanation=ensemble_res.explanation.dict(),
    )


@router.get(
    "/ensemble/weights/grid",
    response_model=SpatialWeightGridResponse | SpatialLeadTimeWeightGridResponse,
)
async def get_ensemble_weights_grid(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variable: str = Query("temperature_2m"),
    lead_time_hours: float | None = Query(
        None, description="If provided, calculates joint spatial x lead-time skill"
    ),
    grid_size: int = Query(5, ge=3, le=9),
    step: float = Query(0.25, ge=0.1, le=1.0),
    evaluation_mode: str = Query("RETROSPECTIVE"),
    causal_cutoff: datetime | None = Query(None),
    target_forecast_time: datetime | None = Query(None),
):
    """Fetch spatial model weight grid for map visualization.

    Returns explicit spatial weights matching the currently evaluated historical region.
    Un-evaluated regions correctly report UNAVAILABLE to prevent misleading extrapolation.
    """
    try:
        if lead_time_hours is not None:
            from forecast_forge.spatial.grid_service import build_spatial_lead_time_weights_grid

            return await build_spatial_lead_time_weights_grid(
                center_lat=latitude,
                center_lon=longitude,
                lead_time_hours=lead_time_hours,
                variable=variable,
                grid_size=grid_size,
                step=step,
                evaluation_mode=evaluation_mode,
                causal_cutoff=causal_cutoff,
                target_forecast_time=target_forecast_time,
            )
        else:
            from forecast_forge.spatial.grid_service import build_spatial_weights_grid

            return await build_spatial_weights_grid(
                center_lat=latitude,
                center_lon=longitude,
                variable=variable,
                grid_size=grid_size,
                step=step,
            )
    except Exception as e:
        raise APIException("WEIGHT_GRID_ERROR", str(e), status_code=500) from e


@router.get("/ensemble/weights/regime", response_model=RegimeWeightResponse)
async def get_ensemble_weights_regime(
    regime_id: int = Query(..., description="Weather regime identifier"),
    lead_time_hours: float = Query(..., description="Target lead time in hours"),
    variable: str = Query("temperature_2m"),
):
    """Fetch regime-conditioned historical model weights."""
    from pathlib import Path

    import pandas as pd

    path = Path("data/processed/mumbai_regime_weights.parquet")
    if not path.exists():
        return RegimeWeightResponse(
            target_lead_time_hours=lead_time_hours,
            regime_id=regime_id,
            weights=[],
            status="UNAVAILABLE",
        )

    try:
        df = pd.read_parquet(path)
        subset = df[
            (df["regime_id"] == regime_id)
            & (df["lead_time_hours"] == lead_time_hours)
            & (df["variable"] == variable)
        ]

        records = []
        for _, row in subset.iterrows():
            records.append(
                RegimeWeightRecord(
                    target_lead_time_hours=lead_time_hours,
                    regime_id=regime_id,
                    model=row["model"],
                    variable=row["variable"],
                    weight=float(row["weight"]),
                    mae=float(row["mae"]) if pd.notna(row["mae"]) else None,
                    rmse=float(row["rmse"]) if pd.notna(row["rmse"]) else None,
                    bias=float(row["bias"]) if pd.notna(row["bias"]) else None,
                    sample_count=int(row["sample_count"]),
                    status=row["status"],
                )
            )

        return RegimeWeightResponse(
            target_lead_time_hours=lead_time_hours,
            regime_id=regime_id,
            weights=records,
            status="AVAILABLE" if records else "NOT_FOUND",
        )
    except Exception as e:
        raise APIException("REGIME_WEIGHT_ERROR", str(e), status_code=500) from e
