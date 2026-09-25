"""Schemas for the unified Decision Trace system."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import Location


class TraceContext(BaseModel):
    """Context of the forecast request."""

    variable: WeatherVariable
    valid_time: datetime
    lead_time_hours: int
    forecast_run: datetime | None = None


class TraceForecast(BaseModel):
    """The final blended forecast decision."""

    model: str = "Forecast Forge Ensemble"
    value: float | None
    unit: str
    status: str
    source: str
    valid_time: datetime
    provenance: str


class WeightEvidence(BaseModel):
    """Evidence for a specific model's weight assignment."""

    model: str
    weight: float
    weight_method: str
    rmse: float | None = None
    mae: float | None = None
    bias: float | None = None
    sample_count: int | None = None
    spatial_scope: str | None = None
    lead_time_hours: int | None = None
    status: str
    provenance: str


class RegimeTrace(BaseModel):
    """Trace of weather regime assignment."""

    regime_id: int | None
    description: str | None = None
    model_version: str | None = None
    feature_snapshot: dict[str, float] | None = None
    scaler_version: str | None = None
    assignment_timestamp: datetime | None = None
    causal_cutoff: datetime | None = None
    model_hash: str | None = None
    status: str
    provenance: str


class ProbabilisticTrace(BaseModel):
    """Trace of probabilistic ensemble state."""

    model: str
    member_count: int
    valid_member_count: int
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None
    event_probabilities: dict[str, float] | None = None
    status: str
    provenance: str


class ExtremeGuidanceTrace(BaseModel):
    """Trace of extreme weather guidance."""

    event_type: str
    variable: str
    operator: str
    threshold: float
    probability: float | None
    valid_member_count: int | None = None
    total_member_count: int | None = None
    probability_method: str | None = None
    status: str
    provenance: str


class BustTrace(BaseModel):
    """Trace of forecast bust detection."""

    signal: str
    bust_definition: str | None = None
    threshold: float | None = None
    threshold_quantile: float | None = None
    lead_time: int | None = None
    feature_snapshot: dict[str, float] | None = None
    feature_contributions: dict[str, float] | None = None
    model_version: str | None = None
    training_cutoff: datetime | None = None
    model_hash: str | None = None
    status: str
    provenance: str


class VerificationTrace(BaseModel):
    """Separate later verification."""

    reference_value: float | None = None
    error: float | None = None
    reference_source: str
    status: str


class DecisionTrace(BaseModel):
    """The unified, machine-readable provenance contract."""

    trace_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    location: Location
    request_context: TraceContext
    decision_integrity: str  # EXACT, DEGRADED, UNAVAILABLE

    forecast: TraceForecast
    model_inputs: dict[str, float | None]
    weights: list[WeightEvidence]
    regime: RegimeTrace
    probabilistic: ProbabilisticTrace | None = None
    extreme_guidance: list[ExtremeGuidanceTrace] = []
    bust_signal: BustTrace
    verification: VerificationTrace
    limitations: list[str] = []
