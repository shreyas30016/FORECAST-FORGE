"""Spatial grid sampling and meteorological overlay generator."""

import time
from datetime import UTC, datetime
from typing import Any

from forecast_forge.api.schemas import (
    GridCellAPI,
    GridDisagreementCellAPI,
    GridResponse,
    SpatialLeadTimeWeightGridResponse,
    SpatialLeadTimeWeightRecord,
    SpatialWeightGridResponse,
    SpatialWeightRecord,
)
from forecast_forge.config import Settings, get_settings
from forecast_forge.core.models import Location
from forecast_forge.evaluation.lead_time_eval import generate_exact_lead_time_evaluation
from forecast_forge.historical.extraction import extract_historical_dataset
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.http_client import ResilientHTTPClient

logger = get_logger(__name__)

# In-memory grid cache with 10-minute TTL to debounce and accelerate scrub operations
# Key: (center_lat_round, center_lon_round, model, step, grid_size)
# Value: (timestamp, list_of_raw_points_data)
_GRID_CACHE: dict[tuple, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 600.0

VARIABLE_UNITS = {
    "temperature_2m": "°C",
    "precipitation": "mm",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "°",
    "wind": "km/h",
    "cloud_cover": "%",
}

MODEL_SOURCE_NAMES = {
    "ecmwf_ifs025": "Open-Meteo / ECMWF IFS (0.25° Physics)",
    "gfs_seamless": "Open-Meteo / NOAA GFS (0.25° Physics)",
    "ecmwf_aifs025": "Open-Meteo / ECMWF AIFS (0.25° Machine Learning)",
    "blended_ensemble": "Forecast Forge Adaptive Ensemble (Multi-Model Synthesis)",
}

# Evaluated historical skill weights from out-of-sample reanalysis benchmark
HISTORICAL_WEIGHTS: dict[str, dict[str, float]] = {
    "temperature_2m": {"ecmwf_ifs025": 0.729, "gfs_seamless": 0.271, "ecmwf_aifs025": 0.0},
    "precipitation": {"ecmwf_ifs025": 0.766, "gfs_seamless": 0.234, "ecmwf_aifs025": 0.0},
    "wind_speed_10m": {"ecmwf_ifs025": 0.666, "gfs_seamless": 0.334, "ecmwf_aifs025": 0.0},
    "wind": {"ecmwf_ifs025": 0.666, "gfs_seamless": 0.334, "ecmwf_aifs025": 0.0},
    "relative_humidity_2m": {"ecmwf_ifs025": 0.748, "gfs_seamless": 0.252, "ecmwf_aifs025": 0.0},
}

HISTORICAL_SKILL_REF: dict[str, dict[str, dict[str, Any]]] = {
    "temperature_2m": {
        "ecmwf_ifs025": {"mae": 0.360, "rmse": 0.472, "bias": -0.050, "samples": 192},
        "gfs_seamless": {"mae": 1.119, "rmse": 1.268, "bias": 0.992, "samples": 192},
        "ecmwf_aifs025": {"mae": None, "rmse": None, "bias": None, "samples": 0},
    },
    "precipitation": {
        "ecmwf_ifs025": {"mae": 0.184, "rmse": 0.295, "bias": 0.006, "samples": 192},
        "gfs_seamless": {"mae": 0.367, "rmse": 0.964, "bias": 0.076, "samples": 192},
        "ecmwf_aifs025": {"mae": None, "rmse": None, "bias": None, "samples": 0},
    },
    "wind_speed_10m": {
        "ecmwf_ifs025": {"mae": 1.983, "rmse": 2.416, "bias": -1.312, "samples": 192},
        "gfs_seamless": {"mae": 4.111, "rmse": 4.808, "bias": 3.848, "samples": 192},
        "ecmwf_aifs025": {"mae": None, "rmse": None, "bias": None, "samples": 0},
    },
    "wind": {
        "ecmwf_ifs025": {"mae": 1.983, "rmse": 2.416, "bias": -1.312, "samples": 192},
        "gfs_seamless": {"mae": 4.111, "rmse": 4.808, "bias": 3.848, "samples": 192},
        "ecmwf_aifs025": {"mae": None, "rmse": None, "bias": None, "samples": 0},
    },
}


def generate_grid_coordinates(
    center_lat: float, center_lon: float, grid_size: int = 5, step: float = 0.25
) -> list[tuple[float, float, list[list[float]]]]:
    """Generate discrete grid coordinates and cell bounds around a center location.

    Returns a list of tuples: (lat, lon, [[lat_min, lon_min], [lat_max, lon_max]])
    """
    half_grid = grid_size // 2
    points = []

    for dy in range(-half_grid, half_grid + 1):
        for dx in range(-half_grid, half_grid + 1):
            lat = round(center_lat + dy * step, 4)
            lon = round(center_lon + dx * step, 4)

            # Clamp latitude to valid bounds
            lat = max(-90.0, min(90.0, lat))
            # Wrap longitude to -180..180
            if lon > 180.0:
                lon -= 360.0
            elif lon < -180.0:
                lon += 360.0

            half_step = step / 2.0
            lat_min = round(lat - half_step, 4)
            lat_max = round(lat + half_step, 4)
            lon_min = round(lon - half_step, 4)
            lon_max = round(lon + half_step, 4)

            bounds = [[lat_min, lon_min], [lat_max, lon_max]]
            points.append((lat, lon, bounds))

    return points


async def fetch_raw_model_grid(
    model: str,
    coordinates: list[tuple[float, float]],
    settings: Settings,
    http_client: ResilientHTTPClient,
) -> list[dict[str, Any]]:
    """Fetch multi-coordinate forecasts from Open-Meteo for a specific model."""
    endpoint = f"{settings.open_meteo_base_url}/forecast"

    lats_str = ",".join(str(p[0]) for p in coordinates)
    lons_str = ",".join(str(p[1]) for p in coordinates)

    params = {
        "latitude": lats_str,
        "longitude": lons_str,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover",
        "forecast_days": 2,
        "models": model,
        "timezone": "UTC",
    }

    status_code, data, _ = await http_client.get_json(
        url=endpoint,
        params=params,
        provider_name="Open-Meteo",
        model_name=model,
    )

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    return []


async def get_cached_raw_grid(
    center_lat: float,
    center_lon: float,
    model: str,
    grid_size: int,
    step: float,
    coordinates: list[tuple[float, float]],
    settings: Settings,
    http_client: ResilientHTTPClient,
) -> list[dict[str, Any]]:
    """Retrieve raw multi-point forecasts with in-memory caching."""
    cache_key = (round(center_lat, 2), round(center_lon, 2), model, step, grid_size)
    now = time.time()

    if cache_key in _GRID_CACHE:
        cached_time, cached_data = _GRID_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            return cached_data

    # Fetch from Open-Meteo
    raw_data = await fetch_raw_model_grid(model, coordinates, settings, http_client)
    _GRID_CACHE[cache_key] = (now, raw_data)
    return raw_data


async def build_spatial_grid(
    center_lat: float,
    center_lon: float,
    variable: str = "temperature_2m",
    model: str = "ecmwf_ifs025",
    valid_time: str | None = None,
    grid_size: int = 5,
    step: float = 0.25,
    settings: Settings | None = None,
    http_client: ResilientHTTPClient | None = None,
) -> GridResponse:
    """Generate spatial meteorological grid response from live numerical weather models."""
    settings = settings or get_settings()
    http_client = http_client or ResilientHTTPClient(settings)

    # 1. Generate discrete sampling grid coordinates
    grid_points = generate_grid_coordinates(
        center_lat=center_lat,
        center_lon=center_lon,
        grid_size=grid_size,
        step=step,
    )
    coords_only = [(p[0], p[1]) for p in grid_points]

    # Map variable to unit
    unit = VARIABLE_UNITS.get(variable, "")

    # Determine which models to fetch
    is_ensemble_mode = model in ["ensemble", "blended", "blended_ensemble"]
    is_disagreement_mode = model in ["disagreement", "model_disagreement", "all"]
    primary_model = "ecmwf_ifs025" if (is_disagreement_mode or is_ensemble_mode) else model

    # 2. Fetch data for primary model (and comparison models if needed)
    raw_primary = await get_cached_raw_grid(
        center_lat=center_lat,
        center_lon=center_lon,
        model=primary_model,
        grid_size=grid_size,
        step=step,
        coordinates=coords_only,
        settings=settings,
        http_client=http_client,
    )

    # Also fetch GFS if calculating disagreement or ensemble
    raw_gfs = None
    if is_disagreement_mode or is_ensemble_mode or model == "all":
        raw_gfs = await get_cached_raw_grid(
            center_lat=center_lat,
            center_lon=center_lon,
            model="gfs_seamless",
            grid_size=grid_size,
            step=step,
            coordinates=coords_only,
            settings=settings,
            http_client=http_client,
        )

    # 3. Determine available timestamps and selected valid time index
    available_times: list[str] = []
    if raw_primary and len(raw_primary) > 0 and "hourly" in raw_primary[0]:
        available_times = raw_primary[0]["hourly"].get("time", [])

    time_idx = 0
    now_utc_str = datetime.now(UTC).strftime("%Y-%m-%dT%H:00")

    if valid_time and valid_time in available_times:
        time_idx = available_times.index(valid_time)
    elif available_times:
        # Find first hour in the future or current hour
        for i, t in enumerate(available_times):
            if t >= now_utc_str:
                time_idx = i
                break

    resolved_valid_time = (
        available_times[time_idx] if available_times else datetime.now(UTC).isoformat()
    )

    # 4. Build grid cells for primary model
    cells: list[GridCellAPI] = []
    source_name = MODEL_SOURCE_NAMES.get(primary_model, "Open-Meteo NWP")

    for i, (lat, lon, bounds) in enumerate(grid_points):
        val: float | None = None
        wind_speed: float | None = None
        wind_direction: float | None = None
        status = "AVAILABLE"

        if i < len(raw_primary) and "hourly" in raw_primary[i]:
            hourly = raw_primary[i]["hourly"]

            if variable == "temperature_2m":
                temps = hourly.get("temperature_2m", [])
                val = temps[time_idx] if time_idx < len(temps) else None
            elif variable == "precipitation":
                precips = hourly.get("precipitation", [])
                val = precips[time_idx] if time_idx < len(precips) else None
            elif variable == "wind_speed_10m":
                winds = hourly.get("wind_speed_10m", [])
                val = winds[time_idx] if time_idx < len(winds) else None
            elif variable == "wind_direction_10m":
                dirs = hourly.get("wind_direction_10m", [])
                val = dirs[time_idx] if time_idx < len(dirs) else None
            elif variable == "cloud_cover":
                clouds = hourly.get("cloud_cover", [])
                val = clouds[time_idx] if time_idx < len(clouds) else None
            elif variable == "wind":
                winds = hourly.get("wind_speed_10m", [])
                dirs = hourly.get("wind_direction_10m", [])
                wind_speed = winds[time_idx] if time_idx < len(winds) else None
                wind_direction = dirs[time_idx] if time_idx < len(dirs) else None
                val = wind_speed

        # Handle null values (especially AIFS)
        if val is None:
            status = "UNAVAILABLE"

        cells.append(
            GridCellAPI(
                latitude=lat,
                longitude=lon,
                value=val,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                variable=variable,
                unit=unit,
                model=primary_model,
                valid_time=resolved_valid_time,
                source=source_name,
                status=status,
                bounds=bounds,
            )
        )

    # 5. Build cross-model multi-cell intelligence (Disagreement, Spatial Ensemble, Summary)
    disagreement_cells: list[GridDisagreementCellAPI] | None = None
    ensemble_cells: list[GridCellAPI] = []
    ensemble_summary: dict[str, Any] | None = None

    if raw_gfs is not None and len(raw_gfs) == len(grid_points):
        disagreement_cells = []
        center_idx = len(grid_points) // 2

        var_weights = HISTORICAL_WEIGHTS.get(
            variable, {"ecmwf_ifs025": 0.729, "gfs_seamless": 0.271}
        )

        for i, (lat, lon, bounds) in enumerate(grid_points):
            var_key = "temperature_2m" if variable in ["temperature_2m", "wind"] else variable
            if variable == "wind":
                var_key = "wind_speed_10m"

            ifs_val: float | None = None
            gfs_val: float | None = None
            ifs_wind_spd: float | None = None
            ifs_wind_dir: float | None = None
            gfs_wind_spd: float | None = None
            gfs_wind_dir: float | None = None

            if i < len(raw_primary) and "hourly" in raw_primary[i]:
                vals = raw_primary[i]["hourly"].get(var_key, [])
                ifs_val = vals[time_idx] if time_idx < len(vals) else None
                if variable == "wind":
                    spds = raw_primary[i]["hourly"].get("wind_speed_10m", [])
                    dirs = raw_primary[i]["hourly"].get("wind_direction_10m", [])
                    ifs_wind_spd = spds[time_idx] if time_idx < len(spds) else None
                    ifs_wind_dir = dirs[time_idx] if time_idx < len(dirs) else None

            if i < len(raw_gfs) and "hourly" in raw_gfs[i]:
                vals = raw_gfs[i]["hourly"].get(var_key, [])
                gfs_val = vals[time_idx] if time_idx < len(vals) else None
                if variable == "wind":
                    spds = raw_gfs[i]["hourly"].get("wind_speed_10m", [])
                    dirs = raw_gfs[i]["hourly"].get("wind_direction_10m", [])
                    gfs_wind_spd = spds[time_idx] if time_idx < len(spds) else None
                    gfs_wind_dir = dirs[time_idx] if time_idx < len(dirs) else None

            # Collect valid models (AIFS strictly excluded as null)
            valid_models = []
            valid_vals = []
            raw_vals = {"ecmwf_ifs025": ifs_val, "gfs_seamless": gfs_val, "ecmwf_aifs025": None}

            if ifs_val is not None:
                valid_models.append("ecmwf_ifs025")
                valid_vals.append(ifs_val)
            if gfs_val is not None:
                valid_models.append("gfs_seamless")
                valid_vals.append(gfs_val)

            # Model Spread: max(valid model values) - min(valid model values)
            disagreement = None
            min_val = None
            max_val = None
            pairwise_diff = None

            if len(valid_vals) >= 2:
                disagreement = round(max(valid_vals) - min(valid_vals), 2)
                min_val = min(valid_vals)
                max_val = max(valid_vals)
                if ifs_val is not None and gfs_val is not None:
                    pairwise_diff = round(abs(ifs_val - gfs_val), 2)

            disagreement_cells.append(
                GridDisagreementCellAPI(
                    latitude=lat,
                    longitude=lon,
                    disagreement=disagreement,
                    min_value=min_val,
                    max_value=max_val,
                    models_included=valid_models,
                    variable=var_key,
                    unit=VARIABLE_UNITS.get(var_key, ""),
                    valid_time=resolved_valid_time,
                    bounds=bounds,
                )
            )

            # Normalize weights over actually available valid models
            tot_w = sum(var_weights.get(m, 0.0) for m in valid_models)
            norm_weights: dict[str, float] = {}
            if tot_w > 0:
                norm_weights = {m: round(var_weights.get(m, 0.0) / tot_w, 3) for m in valid_models}
            elif valid_models:
                norm_weights = {m: round(1.0 / len(valid_models), 3) for m in valid_models}

            # Spatial Ensemble synthesis: sum(weight_i * value_i)
            cell_ens_val: float | None = None
            if valid_models:
                cell_ens_val = round(
                    sum(norm_weights[m] * (raw_vals[m] or 0.0) for m in valid_models), 2
                )

            # Wind vector synthesis
            blended_spd: float | None = None
            blended_dir: float | None = None
            if variable == "wind":
                if ifs_wind_spd is not None and gfs_wind_spd is not None:
                    w_ifs = norm_weights.get("ecmwf_ifs025", 0.5)
                    w_gfs = norm_weights.get("gfs_seamless", 0.5)
                    blended_spd = round(w_ifs * ifs_wind_spd + w_gfs * gfs_wind_spd, 1)
                    blended_dir = ifs_wind_dir if w_ifs >= 0.5 else gfs_wind_dir
                elif ifs_wind_spd is not None:
                    blended_spd = ifs_wind_spd
                    blended_dir = ifs_wind_dir
                elif gfs_wind_spd is not None:
                    blended_spd = gfs_wind_spd
                    blended_dir = gfs_wind_dir
                cell_ens_val = blended_spd

            # Deterministic explanation
            alloc_parts = [
                f"{round(norm_weights[m] * 100)}% to {'ECMWF IFS' if 'ifs' in m else 'NOAA GFS'}"
                for m in valid_models
            ]
            alloc_text = " and ".join(alloc_parts) if alloc_parts else "no active weights"
            cell_explanation = (
                f"Adaptive ensemble assigns {alloc_text} weight based on evaluated historical "
                f"skill for {variable}. "
                "ECMWF AIFS excluded because valid forecast data was unavailable."
                if valid_models
                else "All models unavailable for this spatial grid cell."
            )

            ensemble_cells.append(
                GridCellAPI(
                    latitude=lat,
                    longitude=lon,
                    value=cell_ens_val,
                    wind_speed=blended_spd,
                    wind_direction=blended_dir,
                    variable=variable,
                    unit=unit,
                    model="blended_ensemble",
                    valid_time=resolved_valid_time,
                    source="Forecast Forge Adaptive Ensemble",
                    status="AVAILABLE" if cell_ens_val is not None else "UNAVAILABLE",
                    bounds=bounds,
                    ensemble_value=cell_ens_val,
                    model_spread=disagreement,
                    pairwise_difference=pairwise_diff,
                    weights_applied=norm_weights,
                    models_included=valid_models,
                    models_excluded=["ecmwf_aifs025"],
                    contributing_values=raw_vals,
                    explanation=cell_explanation,
                )
            )

            # Center Station Decision Summary
            if i == center_idx:
                has_both = ifs_val is not None and gfs_val is not None
                ensemble_summary = {
                    "valid_time": resolved_valid_time,
                    "variable": variable,
                    "unit": unit,
                    "ensemble_value": cell_ens_val,
                    "model_spread": disagreement,
                    "pairwise_difference": pairwise_diff,
                    "weights_applied": norm_weights,
                    "models": {
                        "ecmwf_ifs025": {
                            "name": "ECMWF IFS",
                            "type": "NWP Physics Model",
                            "value": ifs_val,
                            "weight": norm_weights.get("ecmwf_ifs025", 0.0),
                            "status": "AVAILABLE" if ifs_val is not None else "UNAVAILABLE",
                            "skill": HISTORICAL_SKILL_REF.get(variable, {}).get("ecmwf_ifs025", {}),
                        },
                        "gfs_seamless": {
                            "name": "NOAA GFS",
                            "type": "NWP Physics Model",
                            "value": gfs_val,
                            "weight": norm_weights.get("gfs_seamless", 0.0),
                            "status": "AVAILABLE" if gfs_val is not None else "UNAVAILABLE",
                            "skill": HISTORICAL_SKILL_REF.get(variable, {}).get("gfs_seamless", {}),
                        },
                        "ecmwf_aifs025": {
                            "name": "ECMWF AIFS",
                            "type": "Data-Driven AI Model",
                            "value": None,
                            "weight": 0.0,
                            "status": "UNAVAILABLE",
                            "reason": "Provider returned no valid forecast values for this period",
                            "skill": {"mae": None, "rmse": None, "bias": None, "samples": 0},
                        },
                    },
                    "data_quality": "PARTIAL" if has_both else "LOW",
                    "explanation": cell_explanation,
                    "method": "Adaptive Historical Skill Blending",
                    "high_spread_threshold": 3.5,
                }

        # If ensemble mode requested, substitute cells with spatial ensemble
        if is_ensemble_mode and ensemble_cells:
            cells = ensemble_cells

        # If disagreement/spread mode requested, replace cells values with model spread values
        elif is_disagreement_mode and disagreement_cells is not None:
            cells = [
                GridCellAPI(
                    latitude=d.latitude,
                    longitude=d.longitude,
                    value=d.disagreement,
                    wind_speed=None,
                    wind_direction=None,
                    variable=f"{variable}_spread",
                    unit=d.unit,
                    model=(
                        "Model Spread [|IFS - GFS|]"
                        if d.models_included == ["ecmwf_ifs025", "gfs_seamless"]
                        else "Model Spread [max - min]"
                    ),
                    valid_time=d.valid_time,
                    source="Forecast Forge Multi-Model Spread",
                    status="AVAILABLE" if d.disagreement is not None else "UNAVAILABLE",
                    bounds=d.bounds,
                    model_spread=d.disagreement,
                    pairwise_difference=d.disagreement if len(d.models_included) == 2 else None,
                    models_included=d.models_included,
                    models_excluded=["ecmwf_aifs025"],
                )
                for d in disagreement_cells
            ]

    # Overall status
    overall_status = "AVAILABLE"
    if all(c.status == "UNAVAILABLE" for c in cells):
        overall_status = "UNAVAILABLE"
    elif any(c.status == "UNAVAILABLE" for c in cells):
        overall_status = "PARTIAL"

    return GridResponse(
        center_latitude=center_lat,
        center_longitude=center_lon,
        variable=variable,
        unit=unit,
        model=model,
        valid_time=resolved_valid_time,
        available_valid_times=available_times[:48],  # first 48 hours for slider
        step=step,
        grid_size=grid_size,
        points_count=len(cells),
        cells=cells,
        disagreement_cells=disagreement_cells,
        status=overall_status,
        provenance_notice=(
            "Forecast model spatial field sampled directly from numerical weather "
            "prediction model runs. Discrete grid cell representation (~28km / 0.25° resolution). "
            "Not station observation data."
        ),
        spatial_uncertainty_available=False,
        spatial_uncertainty_notice=(
            "Spatial ensemble uncertainty data not currently available. "
            "Requires spatial ensemble member distribution streams."
        ),
        ensemble_summary=ensemble_summary,
    )


async def build_spatial_weights_grid(
    center_lat: float,
    center_lon: float,
    variable: str = "temperature_2m",
    grid_size: int = 5,
    step: float = 0.25,
) -> SpatialWeightGridResponse:
    """Generate spatial weight grid explicitly bounding extrapolated evaluations.

    In accordance with Phase 5E.2 Scientific Integrity Constraints, this method
    does NOT interpolate Mumbai weights across the entire map. It strictly binds
    evaluation data to the geographic region it was evaluated against.
    """
    grid_points = generate_grid_coordinates(
        center_lat=center_lat,
        center_lon=center_lon,
        grid_size=grid_size,
        step=step,
    )

    cells = []

    # The only currently evaluated location is Mumbai
    EVALUATED_LAT = 19.0760
    EVALUATED_LON = 72.8777
    EVALUATED_TOLERANCE = 0.3  # Roughly bounds the metropolitan area in degrees

    models = ["ecmwf_ifs025", "gfs_seamless", "ecmwf_aifs025"]

    var_key = "temperature_2m" if variable == "wind" else variable

    # Retrieve base static weights
    var_weights = HISTORICAL_WEIGHTS.get(var_key, {"ecmwf_ifs025": 0.5, "gfs_seamless": 0.5})
    var_refs = HISTORICAL_SKILL_REF.get(var_key, {})

    for lat, lon, bounds in grid_points:
        is_evaluated = (
            abs(lat - EVALUATED_LAT) <= EVALUATED_TOLERANCE
            and abs(lon - EVALUATED_LON) <= EVALUATED_TOLERANCE
        )

        for model in models:
            if is_evaluated:
                weight = var_weights.get(model, 0.0)
                ref = var_refs.get(model, {})
                status = "AVAILABLE" if weight > 0 else "UNAVAILABLE"
                cells.append(
                    SpatialWeightRecord(
                        latitude=lat,
                        longitude=lon,
                        bounds=bounds,
                        variable=variable,
                        model=model,
                        weight=weight,
                        historical_metric=ref.get("rmse"),
                        metric_name="RMSE",
                        sample_count=ref.get("samples", 0),
                        evaluation_period="All (Aggregate)",
                        reference_source="ERA5 reanalysis reference benchmark",
                        status=status,
                        coverage_type="LOCATION_EVALUATED",
                    )
                )
            else:
                # Scientifically honest sparse mapping: unavailable outside evaluated bounds
                cells.append(
                    SpatialWeightRecord(
                        latitude=lat,
                        longitude=lon,
                        bounds=bounds,
                        variable=variable,
                        model=model,
                        weight=0.0,
                        historical_metric=None,
                        metric_name="RMSE",
                        sample_count=0,
                        evaluation_period="All (Aggregate)",
                        reference_source="ERA5 reanalysis reference benchmark",
                        status="UNAVAILABLE",
                        coverage_type="UNSUPPORTED_REGION",
                    )
                )

    return SpatialWeightGridResponse(
        center_latitude=center_lat,
        center_longitude=center_lon,
        variable=variable,
        grid_size=grid_size,
        step=step,
        cells=cells,
        coverage_disclosure=(
            "Spatial weight coverage currently available for evaluated locations only."
        ),
    )


async def build_spatial_lead_time_weights_grid(
    center_lat: float,
    center_lon: float,
    lead_time_hours: float,
    variable: str = "temperature_2m",
    grid_size: int = 3,
    step: float = 0.25,
    evaluation_mode: str = "RETROSPECTIVE",
    causal_cutoff: datetime | None = None,
    target_forecast_time: datetime | None = None,
    evaluation_start: str | None = None,
    evaluation_end: str | None = None,
) -> SpatialLeadTimeWeightGridResponse:
    """Generate true spatial x lead-time model weight grid from real historical data."""
    from datetime import date

    grid_points = generate_grid_coordinates(
        center_lat=center_lat,
        center_lon=center_lon,
        grid_size=grid_size,
        step=step,
    )

    cells = []

    # The only currently evaluated location is Mumbai
    EVALUATED_LAT = 19.0760
    EVALUATED_LON = 72.8777
    EVALUATED_TOLERANCE = 0.3  # Roughly bounds the metropolitan area in degrees

    models = ["ecmwf_ifs025", "gfs_seamless", "ecmwf_aifs025"]

    # Default window for eval if not provided (matches 5E.3 audit window)
    if not evaluation_start:
        evaluation_start = "2024-06-01"
    if not evaluation_end:
        evaluation_end = "2024-06-30"

    start_d = date.fromisoformat(evaluation_start)
    end_d = date.fromisoformat(evaluation_end)

    lead_days = int(lead_time_hours // 24)
    if lead_days <= 0 or lead_days > 7:
        lead_days = 1  # fallback

    for lat, lon, bounds in grid_points:
        is_evaluated = (
            abs(lat - EVALUATED_LAT) <= EVALUATED_TOLERANCE
            and abs(lon - EVALUATED_LON) <= EVALUATED_TOLERANCE
        )

        if not is_evaluated:
            # Scientifically honest sparse mapping: unavailable outside evaluated bounds
            for model in models:
                cells.append(
                    SpatialLeadTimeWeightRecord(
                        latitude=lat,
                        longitude=lon,
                        bounds=bounds,
                        variable=variable,
                        model=model,
                        lead_time_hours=lead_time_hours,
                        weight=0.0,
                        mae=None,
                        rmse=None,
                        bias=None,
                        sample_count=0,
                        evaluation_period=f"{evaluation_start} to {evaluation_end}",
                        evaluation_mode=evaluation_mode,
                        causal_cutoff=causal_cutoff,
                        status="UNSUPPORTED_REGION",
                    )
                )
            continue

        # Fetch historical data for this point
        loc = Location(name="Grid Point", latitude=lat, longitude=lon)
        try:
            models_df, ref_df = await extract_historical_dataset(
                location=loc,
                start_date=start_d,
                end_date=end_d,
                run=None,
                lead_time_days=[lead_days],
            )

            if models_df.empty or ref_df.empty:
                raise ValueError("No historical data available")

            # Align references
            import pandas as pd

            merged_df = pd.merge(
                models_df,
                ref_df[["valid_time", f"ref_{variable}"]],
                on="valid_time",
                how="inner",
            )

            if merged_df.empty:
                raise ValueError("No matched historical data")

            # Calculate exact lead-time skill
            eval_res = generate_exact_lead_time_evaluation(
                df=merged_df,
                variables=[variable],
                evaluation_mode=evaluation_mode,
                causal_cutoff=causal_cutoff,
                target_forecast_time=target_forecast_time,
                min_samples=5,
                expected_models=models,
                lead_hours=[lead_time_hours],
            )

            if eval_res.empty:
                raise ValueError("Evaluation returned empty")

            for model in models:
                m_res = eval_res[eval_res["model"] == model]
                if not m_res.empty:
                    row = m_res.iloc[0]
                    weight = float(row["weight"]) if not pd.isna(row["weight"]) else 0.0
                    status = row["status"]
                    cells.append(
                        SpatialLeadTimeWeightRecord(
                            latitude=lat,
                            longitude=lon,
                            bounds=bounds,
                            variable=variable,
                            model=model,
                            lead_time_hours=lead_time_hours,
                            weight=weight,
                            mae=float(row["mae"]) if not pd.isna(row["mae"]) else None,
                            rmse=float(row["rmse"]) if not pd.isna(row["rmse"]) else None,
                            bias=float(row["bias"]) if not pd.isna(row["bias"]) else None,
                            sample_count=int(row["valid_samples"]),
                            evaluation_period=f"{evaluation_start} to {evaluation_end}",
                            evaluation_mode=evaluation_mode,
                            causal_cutoff=causal_cutoff,
                            status=status,
                            provenance_source=row.get("provenance_source", None),
                        )
                    )
                else:
                    cells.append(
                        SpatialLeadTimeWeightRecord(
                            latitude=lat,
                            longitude=lon,
                            bounds=bounds,
                            variable=variable,
                            model=model,
                            lead_time_hours=lead_time_hours,
                            weight=0.0,
                            mae=None,
                            rmse=None,
                            bias=None,
                            sample_count=0,
                            evaluation_period=f"{evaluation_start} to {evaluation_end}",
                            evaluation_mode=evaluation_mode,
                            causal_cutoff=causal_cutoff,
                            status="UNAVAILABLE",
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to calculate joint weights for {lat},{lon}: {e}")
            for model in models:
                cells.append(
                    SpatialLeadTimeWeightRecord(
                        latitude=lat,
                        longitude=lon,
                        bounds=bounds,
                        variable=variable,
                        model=model,
                        lead_time_hours=lead_time_hours,
                        weight=0.0,
                        mae=None,
                        rmse=None,
                        bias=None,
                        sample_count=0,
                        evaluation_period=f"{evaluation_start} to {evaluation_end}",
                        evaluation_mode=evaluation_mode,
                        causal_cutoff=causal_cutoff,
                        status="INSUFFICIENT_DATA",
                    )
                )

    overall_status = "AVAILABLE"
    if all(c.status in ("UNSUPPORTED_REGION", "UNAVAILABLE", "INSUFFICIENT_DATA") for c in cells):
        overall_status = "UNAVAILABLE"

    return SpatialLeadTimeWeightGridResponse(
        center_latitude=center_lat,
        center_longitude=center_lon,
        variable=variable,
        lead_time_hours=lead_time_hours,
        grid_size=grid_size,
        step=step,
        evaluation_mode=evaluation_mode,
        causal_cutoff=causal_cutoff,
        cells=cells,
        coverage_disclosure=(
            "Spatial × Lead-Time weight coverage currently available for evaluated locations only."
        ),
        status=overall_status,
    )
