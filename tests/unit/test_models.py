"""Unit tests for canonical data models and schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.models import (
    ForecastPoint,
    ForecastRequest,
    Location,
    ProviderResult,
)


def test_location_valid():
    """Verify valid coordinates create a Location model."""
    loc = Location(latitude=19.076, longitude=72.8777, name="Mumbai", timezone="Asia/Kolkata")
    assert loc.latitude == 19.076
    assert loc.longitude == 72.8777
    assert loc.name == "Mumbai"
    assert loc.timezone == "Asia/Kolkata"


def test_location_invalid_latitude():
    """Verify latitude beyond [-90, 90] raises ValidationError."""
    with pytest.raises(ValidationError):
        Location(latitude=91.0, longitude=0.0)

    with pytest.raises(ValidationError):
        Location(latitude=-90.1, longitude=0.0)


def test_location_invalid_longitude():
    """Verify longitude beyond [-180, 180] raises ValidationError."""
    with pytest.raises(ValidationError):
        Location(latitude=0.0, longitude=180.1)

    with pytest.raises(ValidationError):
        Location(latitude=0.0, longitude=-180.1)


def test_forecast_point_utc_coercion():
    """Verify naive datetime is converted to UTC timezone-aware datetime."""
    naive_dt = datetime(2026, 9, 22, 12, 0, 0)
    point = ForecastPoint(
        timestamp=naive_dt,
        latitude=19.076,
        longitude=72.8777,
        temperature_2m=27.5,
        provider="Open-Meteo",
        model="ecmwf_ifs025",
    )
    assert point.timestamp.tzinfo is not None
    assert point.timestamp.tzinfo == UTC


def test_forecast_request_defaults():
    """Verify ForecastRequest populates default weather variables and horizon."""
    loc = Location(latitude=19.076, longitude=72.8777)
    req = ForecastRequest(location=loc)
    assert req.forecast_days == 3
    assert WeatherVariable.TEMPERATURE_2M in req.variables
    assert WeatherVariable.PRECIPITATION in req.variables


def test_provider_result_defaults():
    """Verify ProviderResult defaults and status mapping."""
    res = ProviderResult(
        provider_name="Open-Meteo",
        model_name="ecmwf_ifs025",
        status=ProviderStatus.AVAILABLE,
    )
    assert res.total_records == 0
    assert res.valid_records == 0
    assert res.status == ProviderStatus.AVAILABLE
