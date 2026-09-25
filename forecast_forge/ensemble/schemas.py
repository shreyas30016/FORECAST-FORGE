"""Schemas and data models for the ensemble engine."""

from datetime import datetime

from pydantic import BaseModel, Field


class EnsembleWeight(BaseModel):
    """Weight for a single model in an ensemble."""

    model: str
    weight: float


class ModelForecast(BaseModel):
    """Individual model forecast for a specific variable."""

    model: str
    value: float | None
    is_valid: bool
    status: str = Field(
        default="AVAILABLE",
        description="e.g. AVAILABLE, DEGRADED, NO_VALID_DATA, UNAVAILABLE, STALE",
    )


class UncertaintyResult(BaseModel):
    """Uncertainty analysis for the ensemble."""

    spread: float | None = Field(description="Standard deviation across valid model predictions")
    valid_model_count: int = Field(description="Number of models contributing to the ensemble")
    total_model_count: int = Field(description="Total number of models evaluated")
    data_quality_indicator: str = Field(
        description="e.g. HIGH, PARTIAL, POOR based on missing models"
    )


class EnsembleExplanation(BaseModel):
    """Explanation of how the ensemble was formed."""

    primary_contributor: str | None
    dropped_models: list[str]
    reasoning: str


class EnsembleResult(BaseModel):
    """The final generated ensemble forecast."""

    location_name: str
    variable: str
    valid_time: datetime

    # Inputs
    model_forecasts: list[ModelForecast]

    # Baselines
    equal_weight_forecast: float | None
    inverse_error_forecast: float | None

    # Adaptive
    adaptive_forecast: float | None
    adaptive_weights: list[EnsembleWeight] | None

    # Meta
    uncertainty: UncertaintyResult
    explanation: EnsembleExplanation


class ProbabilisticForecast(BaseModel):
    """Structured probabilistic representation from true ensemble members."""

    model: str
    variable: str
    valid_time: datetime
    latitude: float
    longitude: float
    lead_time_hours: int | None = None

    member_count: int
    valid_member_count: int

    p10: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    p90: float | None

    mean: float | None
    median: float | None
    spread: float | None = Field(default=None, description="Standard deviation among valid members")

    status: str = Field(
        default="AVAILABLE",
        description="e.g. AVAILABLE, UNAVAILABLE, INSUFFICIENT_DATA",
    )
    provenance: str = Field(description="Description of the source data")


class EventProbabilityRequest(BaseModel):
    """Request for a probabilistic threshold."""

    variable: str
    operator: str = Field(description="e.g. '>', '>=', '<', '<='")
    threshold: float


class EventProbabilityResult(BaseModel):
    """Empirical event probability from ensemble members."""

    variable: str
    operator: str
    threshold: float
    probability: float | None
    valid_member_count: int
    status: str
