"""Canonical data models and schemas for Forecast Forge AI."""

from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from forecast_forge.core.enums import ProviderStatus, WeatherVariable


class Location(BaseModel):
    """Geographical target coordinates and metadata."""

    latitude: Annotated[float, Field(ge=-90.0, le=90.0, description="Latitude in degrees")]
    longitude: Annotated[float, Field(ge=-180.0, le=180.0, description="Longitude in degrees")]
    name: str | None = Field(default=None, description="Human-readable location name")
    timezone: str = Field(default="UTC", description="Target timezone name")


class ForecastRequest(BaseModel):
    """Normalized request parameters for querying weather forecasts."""

    location: Location
    variables: list[WeatherVariable] = Field(
        default_factory=lambda: [
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
            WeatherVariable.CLOUD_COVER,
        ],
        description="List of weather variables to retrieve",
    )
    forecast_days: int = Field(
        default=3,
        ge=1,
        le=16,
        description="Horizon in forecast days",
    )


class HistoricalRequest(BaseModel):
    """Normalized request parameters for querying historical weather forecasts."""

    location: Location
    start_date: date = Field(description="Start date of the historical period")
    end_date: date = Field(description="End date of the historical period")
    run: datetime | None = Field(default=None, description="Exact model initialization time")
    lead_time_days: list[int] | None = Field(
        default=None, description="Specific previous lead days to retrieve (1-7)"
    )
    variables: list[WeatherVariable] = Field(
        default_factory=lambda: [
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
            WeatherVariable.CLOUD_COVER,
        ],
        description="List of weather variables to retrieve",
    )


class ForecastPoint(BaseModel):
    """Canonical single-timestep forecast data point."""

    timestamp: datetime = Field(description="Forecast valid time in UTC")
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    temperature_2m: float | None = Field(
        default=None, description="2m air temperature in degrees Celsius"
    )
    precipitation: float | None = Field(
        default=None, description="Precipitation amount in millimeters"
    )
    wind_speed_10m: float | None = Field(
        default=None, description="10m wind speed in kilometers per hour"
    )
    relative_humidity_2m: float | None = Field(
        default=None, description="2m relative humidity percentage"
    )
    cloud_cover: float | None = Field(default=None, description="Cloud cover percentage")
    provider: str = Field(description="Name of the data provider source")
    model: str = Field(description="Identifier of the numerical weather prediction model")
    units: dict[str, str] = Field(
        default_factory=dict, description="Mapping of variable names to units"
    )
    initialization_time: datetime | None = Field(
        default=None, description="Model initialization run timestamp"
    )
    lead_time_hours: float | None = Field(
        default=None, description="Forecast lead time in hours from initialization"
    )
    lead_time_semantics: str | None = Field(
        default=None,
        description="Semantics of lead time: 'FIXED_LEAD_OFFSET', 'EXACT_RUN_CYCLE', or None",
    )
    provenance_source: str | None = Field(
        default=None,
        description="Data source or provider endpoint used for provenance tracking",
    )
    retrieval_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when data was fetched",
    )

    @field_validator("timestamp", mode="after")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure all timestamps are timezone-aware and set to UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    @field_validator("initialization_time", mode="after")
    @classmethod
    def ensure_init_utc(cls, v: datetime | None) -> datetime | None:
        """Ensure initialization timestamp is timezone-aware and set to UTC."""
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def validate_temporal_causality(self) -> "ForecastPoint":
        """Reject causality violations: valid_time must not precede initialization_time."""
        if self.initialization_time is not None:
            if self.timestamp < self.initialization_time:
                raise ValueError(
                    f"Causality violation: valid_time ({self.timestamp}) is before "
                    f"initialization_time ({self.initialization_time})"
                )
        return self


class ProviderResult(BaseModel):
    """Normalized result returned by a weather provider adapter."""

    provider_name: str
    model_name: str
    status: ProviderStatus
    records: list[ForecastPoint] = Field(default_factory=list)
    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response_status_code: int | None = None
    total_records: int = 0
    valid_records: int = 0
    missing_variables_count: int = 0
    latency_ms: float = 0.0
    error_message: str | None = None
    raw_units: dict[str, str] = Field(default_factory=dict)
