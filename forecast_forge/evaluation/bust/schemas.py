"""Schemas for Forecast-Bust Intelligence."""

from pydantic import BaseModel, Field


class BustFactor(BaseModel):
    name: str = Field(description="Name of the contributing factor")
    contribution: float = Field(description="Relative weight/contribution of this factor")
    direction: str = Field(description="POSITIVE (increases bust likelihood) or NEGATIVE")


class ForecastBustSignal(BaseModel):
    signal: str = Field(description="NORMAL, ELEVATED, or INSUFFICIENT_DATA")
    variable: str
    lead_time_hours: float
    bust_threshold: float | None = Field(
        default=None, description="The historical error threshold defining a bust"
    )
    historical_error_quantile: float = Field(
        default=0.90, description="Quantile used for the threshold"
    )
    primary_factors: list[BustFactor] = Field(
        default_factory=list, description="Explainability factors"
    )
    regime_context: str | None = Field(default=None, description="Regime evidence")
    status: str = Field(default="AVAILABLE")
    provenance: str = Field(default="Logistic Regression on Causal Features")
