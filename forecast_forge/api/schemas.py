"""API request and response schemas for FastAPI layer."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------
# Error Schemas
# ---------------------------------------------------------


class APIErrorDetails(BaseModel):
    code: str
    message: str
    details: dict | None = None


class APIErrorResponse(BaseModel):
    error: APIErrorDetails


# ---------------------------------------------------------
# Health Schemas
# ---------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class DataSourceHealth(BaseModel):
    provider: str
    model: str
    status: str
    last_checked: datetime | None = None
    reason: str | None = None


# ---------------------------------------------------------
# Models Schemas
# ---------------------------------------------------------


class ModelInfo(BaseModel):
    name: str
    provider: str
    status: str
    capabilities: list[str]
    last_checked: datetime | None = None
    available_variables: list[str]
    supported_forecast_horizon_hours: int
    reason: str | None = None


# ---------------------------------------------------------
# Forecast & Ensemble Schemas
# ---------------------------------------------------------


class LocationAPI(BaseModel):
    name: str | None = None
    latitude: float
    longitude: float


class ModelForecastAPI(BaseModel):
    status: str
    forecast: float | None
    weight: float


class EnsembleMetaAPI(BaseModel):
    forecast: float | None
    method: str
    uncertainty: float | None
    data_quality: str
    trace_id: str | None = None


class EnsembleResponse(BaseModel):
    location: LocationAPI
    retrieval_timestamp: datetime
    valid_time: datetime
    variable: str
    models: dict[str, ModelForecastAPI]
    ensemble: EnsembleMetaAPI
    explanation: dict | None = None


# ---------------------------------------------------------
# Raw Forecast Response (Non-Ensemble)
# ---------------------------------------------------------


class ForecastPointAPI(BaseModel):
    timestamp: datetime
    temperature_2m: float | None = None
    relative_humidity_2m: float | None = None
    precipitation: float | None = None
    wind_speed_10m: float | None = None


class ProviderResultAPI(BaseModel):
    model: str
    status: str
    records: list[ForecastPointAPI]


class ForecastResponse(BaseModel):
    location: LocationAPI
    retrieval_timestamp: datetime
    providers: dict[str, ProviderResultAPI]


# ---------------------------------------------------------
# Evaluation / Historical Schemas
# ---------------------------------------------------------


class ModelSkillRecord(BaseModel):
    model: str
    variable: str
    lead_time_hours: float | None = None
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    sample_count: int
    evaluation_period: str = "All (Aggregate)"
    reference_source: str = "ERA5 reanalysis reference benchmark"
    status: str = "AVAILABLE"
    initialization_time: datetime | None = None
    lead_time_semantics: str | None = None
    provenance_source: str | None = None
    total_records: int = 0
    valid_forecast_records: int = 0
    valid_reference_records: int = 0
    valid_matched_records: int = 0
    missing_fraction: float = 0.0
    weight: float = 0.0
    evaluation_mode: str = "RETROSPECTIVE"
    causal_cutoff: datetime | None = None


class EvaluationResponse(BaseModel):
    lead_time_available: bool = False
    lead_time_notice: str | None = None
    evaluation_mode: str = "RETROSPECTIVE"
    causal_cutoff: datetime | None = None
    evaluations: list[ModelSkillRecord]


class HistoricalDataAPI(BaseModel):
    location: LocationAPI
    variable: str
    data: list[dict]  # simplified dynamic representation


# ---------------------------------------------------------
# Spatial Grid Schemas (Phase 5D / Phase 5E)
# ---------------------------------------------------------


class GridCellAPI(BaseModel):
    latitude: float
    longitude: float
    value: float | None = None
    wind_direction: float | None = None
    wind_speed: float | None = None
    variable: str
    unit: str
    model: str
    valid_time: str
    source: str
    status: str
    bounds: list[list[float]]
    ensemble_value: float | None = None
    model_spread: float | None = None
    pairwise_difference: float | None = None
    weights_applied: dict[str, float] | None = None
    models_included: list[str] | None = None
    models_excluded: list[str] | None = None
    contributing_values: dict[str, float | None] | None = None
    explanation: str | None = None


class GridDisagreementCellAPI(BaseModel):
    latitude: float
    longitude: float
    disagreement: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    models_included: list[str]
    variable: str
    unit: str
    valid_time: str
    bounds: list[list[float]]


class GridResponse(BaseModel):
    center_latitude: float
    center_longitude: float
    variable: str
    unit: str
    model: str
    valid_time: str
    available_valid_times: list[str]
    step: float
    grid_size: int
    points_count: int
    cells: list[GridCellAPI]
    disagreement_cells: list[GridDisagreementCellAPI] | None = None
    status: str
    provenance_notice: str
    spatial_uncertainty_available: bool = False
    spatial_uncertainty_notice: str | None = None
    ensemble_summary: dict[str, Any] | None = None


# ---------------------------------------------------------
# Spatial Weights (Phase 5E.2)
# ---------------------------------------------------------


class SpatialWeightRecord(BaseModel):
    latitude: float
    longitude: float
    bounds: list[list[float]]
    variable: str
    model: str
    weight: float
    historical_metric: float | None = None
    metric_name: str = "RMSE"
    sample_count: int = 0
    evaluation_period: str = "All (Aggregate)"
    reference_source: str = "ERA5 reanalysis reference benchmark"
    status: str = "AVAILABLE"
    coverage_type: str = "LOCATION_EVALUATED"


class SpatialWeightGridResponse(BaseModel):
    center_latitude: float
    center_longitude: float
    variable: str
    grid_size: int
    step: float
    cells: list[SpatialWeightRecord]
    coverage_disclosure: str
    status: str = "AVAILABLE"


class SpatialLeadTimeWeightRecord(BaseModel):
    latitude: float
    longitude: float
    bounds: list[list[float]]
    variable: str
    model: str
    lead_time_hours: float

    weight: float
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    sample_count: int

    evaluation_period: str = "All (Aggregate)"
    evaluation_mode: str = "RETROSPECTIVE"
    causal_cutoff: datetime | None = None

    reference_source: str = "ERA5 reanalysis reference benchmark"
    lead_time_semantics: str = "FIXED_LEAD_OFFSET"
    provenance_source: str | None = None
    status: str


class SpatialLeadTimeWeightGridResponse(BaseModel):
    center_latitude: float
    center_longitude: float
    variable: str
    lead_time_hours: float
    grid_size: int
    step: float
    evaluation_mode: str = "RETROSPECTIVE"
    causal_cutoff: datetime | None = None
    cells: list[SpatialLeadTimeWeightRecord]
    coverage_disclosure: str
    status: str = "AVAILABLE"


# ---------------------------------------------------------
# Regime Schemas (Phase 5F)
# ---------------------------------------------------------


class RegimeWeightRecord(BaseModel):
    """Model weight conditioned on lead time and current weather regime."""

    target_lead_time_hours: float
    regime_id: int
    model: str
    variable: str
    weight: float
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    sample_count: int
    status: str


class RegimeWeightResponse(BaseModel):
    """API response for regime-conditioned model weights."""

    target_lead_time_hours: float
    regime_id: int
    weights: list[RegimeWeightRecord]
    status: str = "AVAILABLE"
