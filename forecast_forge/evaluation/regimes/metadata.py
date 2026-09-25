"""Metadata definitions for Weather Regime Intelligence."""

from pydantic import BaseModel, Field


class RegimeFeatureSummary(BaseModel):
    """Centroid values for the meteorological features defining a regime."""

    temperature_2m: float | None = Field(default=None, description="Centroid temperature in C")
    relative_humidity_2m: float | None = Field(default=None, description="Centroid RH in %")
    precipitation: float | None = Field(default=None, description="Centroid precipitation in mm")
    wind_speed_10m: float | None = Field(default=None, description="Centroid wind speed in km/h")
    cloud_cover: float | None = Field(default=None, description="Centroid cloud cover in %")


class RegimeDefinition(BaseModel):
    """Metadata describing a single discovered weather regime."""

    regime_id: int = Field(description="Unique integer identifier for the regime")
    description: str = Field(description="Evidence-based meteorological narrative")
    feature_summary: RegimeFeatureSummary = Field(description="Centroid feature statistics")
    sample_count: int = Field(description="Number of historical samples in this regime")
    training_period: str = Field(description="Historical window used for fitting")
    model_version: str = Field(description="Version of the clustering model/scaler")
    provenance: str = Field(default="ERA5_Reanalysis", description="Source data used for discovery")


class RegimeAssignment(BaseModel):
    """Result of assigning a state to a weather regime."""

    regime_id: int | None = Field(description="Assigned regime ID, or None if invalid")
    is_valid: bool = Field(description="Whether the assignment was successful")
    status: str = Field(description="AVAILABLE, UNAVAILABLE, or INSUFFICIENT_DATA")
    missing_features: list[str] = Field(
        default_factory=list, description="Features that were missing"
    )
