"""Schemas for Scientific Forecast Replay."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReplayRegimeSnapshot(BaseModel):
    """Regime context at forecast time."""

    regime_id: int
    regime_model_version: str
    feature_snapshot: dict[str, float]
    assignment_provenance: str
    causal_cutoff: datetime | None = None
    model_hash: str | None = None


class ReplayExtremeSnapshot(BaseModel):
    """Extreme weather guidance at forecast time."""

    event_type: str
    threshold: float
    probability: float | None
    status: str
    provenance: str


class ReplayBustSnapshot(BaseModel):
    """Forecast bust signal at forecast time."""

    signal: str  # "ELEVATED", "NORMAL", "UNAVAILABLE"
    score: float | None
    model_version: str
    provenance: str
    causal_cutoff: datetime | None = None
    model_hash: str | None = None


class ForecastTimeDecision(BaseModel):
    """Immutable snapshot of information known at T0."""

    initialization_time: datetime
    valid_time: datetime
    lead_time_hours: int

    # Deterministic layer
    model_forecasts: dict[str, float | None]
    model_availability: dict[str, str]  # "AVAILABLE", "UNAVAILABLE", etc.

    # Overall Replay Integrity Status
    replay_integrity_status: str = "EXACT"  # "EXACT", "DEGRADED", "UNAVAILABLE"

    # Weights layer (calculated ONLY using data prior to T0)
    spatial_weights: dict[str, float]
    lead_time_weights: dict[str, float]
    final_blended_value: float | None

    # Intelligence layers
    regime: ReplayRegimeSnapshot | None
    probabilistic_summary: dict[str, str] = Field(default_factory=dict)
    probabilistic_status: str = "UNAVAILABLE"
    extreme_guidance: list[ReplayExtremeSnapshot]
    bust_signal: ReplayBustSnapshot

    provenance: str
    data_quality_status: str


class LaterVerification(BaseModel):
    """Verification revealed only after the decision is locked."""

    valid_time: datetime
    reference_value: float | None
    realized_error: float | None
    reference_source: str = "ERA5 reanalysis reference benchmark"


class ReplaySnapshot(BaseModel):
    """A single replay timestep capturing both decision and later verification."""

    replay_id: str
    trace_id: str | None = None
    latitude: float
    longitude: float
    variable: str
    run: datetime

    forecast_time_decision: ForecastTimeDecision
    later_verification: LaterVerification | None


class ReplayTimelineResponse(BaseModel):
    """Complete replay timeline."""

    replay_id: str
    run: datetime
    latitude: float
    longitude: float
    variable: str
    snapshots: list[ReplaySnapshot]
    provenance: str
    status: str
