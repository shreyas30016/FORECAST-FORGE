"""Core enumerations for Forecast Forge AI."""

from enum import StrEnum


class ProviderStatus(StrEnum):
    """Operational status of a weather provider response."""

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    NO_VALID_DATA = "NO_VALID_DATA"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"


class WeatherVariable(StrEnum):
    """Standardized numerical weather variables tracked by the system."""

    TEMPERATURE_2M = "temperature_2m"
    RELATIVE_HUMIDITY_2M = "relative_humidity_2m"
    PRECIPITATION = "precipitation"
    WIND_SPEED_10M = "wind_speed_10m"
    CLOUD_COVER = "cloud_cover"
