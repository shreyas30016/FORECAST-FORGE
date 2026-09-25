"""Schemas for Extreme Weather Guidance."""

from datetime import datetime

from pydantic import BaseModel, Field


class EventDefinition(BaseModel):
    """Configuration for an extreme weather event."""

    event_type: str = Field(description="e.g., Heavy Rain, High Wind")
    variable: str = Field(description="Variable name, e.g., precipitation, wind_speed_10m")
    operator: str = Field(description="e.g., >=, >, <, <=")
    threshold: float
    unit: str


class RegimeContext(BaseModel):
    """Contextual information about the current weather regime."""

    current_regime: str
    regime_id: int
    regime_description: str
    regime_sample_count: int


class HistoricalSkillContext(BaseModel):
    """Contextual historical skill metrics for the current event."""

    lead_time_rmse: float | None = None
    spatial_rmse: float | None = None
    regime_conditioned_rmse: float | None = None


class SpatialContext(BaseModel):
    """Spatial context of the location."""

    latitude: float
    longitude: float
    is_supported: bool


class EventGuidance(BaseModel):
    """Structured guidance response for an extreme event."""

    event_type: str
    threshold: float
    probability: float | None = Field(
        description="Empirical ensemble-member probability. 0 <= prob <= 1"
    )
    probability_method: str = Field(default="empirical ensemble-member probability")
    lead_time_hours: int
    valid_time: datetime
    location: str

    ensemble_member_count: int
    valid_member_count: int

    active_models: list[str]

    regime: RegimeContext | None = None
    historical_skill_context: HistoricalSkillContext | None = None
    spatial_context: SpatialContext

    status: str = Field(
        description="e.g. AVAILABLE, UNAVAILABLE, INSUFFICIENT_DATA, UNSUPPORTED_REGION"
    )
    provenance: str = Field(description="Source of the data")


class EventVerificationResult(BaseModel):
    """Verification metrics for historical events."""

    event_type: str
    threshold: float
    model: str
    lead_time_hours: int
    sample_size: int

    brier_score: float | None = None
    pod: float | None = Field(None, description="Probability of Detection")
    far: float | None = Field(None, description="False Alarm Ratio")
    csi: float | None = Field(None, description="Critical Success Index")

    reference: str = Field(default="ERA5 reanalysis reference benchmark")
