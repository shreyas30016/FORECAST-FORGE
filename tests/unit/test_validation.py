"""Unit tests for domain validation and status calculation."""

from datetime import UTC, datetime

from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.models import ForecastPoint, Location
from forecast_forge.validation.bounds import (
    BOUND_PRECIPITATION,
    BOUND_RELATIVE_HUMIDITY_2M,
    BOUND_TEMPERATURE_2M,
    BOUND_WIND_SPEED_10M,
)
from forecast_forge.validation.validator import ForecastValidator


def test_physical_bounds():
    """Verify boundary checks for each meteorological variable."""
    assert BOUND_TEMPERATURE_2M.is_valid(25.0)
    assert not BOUND_TEMPERATURE_2M.is_valid(-80.0)
    assert not BOUND_TEMPERATURE_2M.is_valid(70.0)
    assert not BOUND_TEMPERATURE_2M.is_valid(None)

    assert BOUND_RELATIVE_HUMIDITY_2M.is_valid(50.0)
    assert not BOUND_RELATIVE_HUMIDITY_2M.is_valid(-1.0)
    assert not BOUND_RELATIVE_HUMIDITY_2M.is_valid(105.0)

    assert BOUND_PRECIPITATION.is_valid(10.0)
    assert not BOUND_PRECIPITATION.is_valid(-0.1)

    assert BOUND_WIND_SPEED_10M.is_valid(30.0)
    assert not BOUND_WIND_SPEED_10M.is_valid(-5.0)


def test_validate_location():
    """Verify coordinate bounding in validator."""
    assert ForecastValidator.validate_location(Location(latitude=19.076, longitude=72.8777))


def test_validate_point_out_of_bounds():
    """Verify points with physically impossible values fail point validation."""
    now = datetime.now(UTC)
    point = ForecastPoint(
        timestamp=now,
        latitude=19.076,
        longitude=72.8777,
        temperature_2m=150.0,  # Physically impossible
        provider="Open-Meteo",
        model="ecmwf_ifs025",
    )
    is_valid, _ = ForecastValidator.validate_point(point)
    assert not is_valid


def test_assess_dataset_status_empty():
    """Verify empty dataset yields NO_VALID_DATA (provider responded, no records built)."""
    status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
        records=[],
        requested_variables=[WeatherVariable.TEMPERATURE_2M],
    )
    assert status == ProviderStatus.NO_VALID_DATA
    assert valid_count == 0


def test_assess_dataset_status_all_null():
    """Verify dataset with all null values yields NO_VALID_DATA (not UNAVAILABLE)."""
    now = datetime.now(UTC)
    records = [
        ForecastPoint(
            timestamp=now,
            latitude=19.076,
            longitude=72.8777,
            temperature_2m=None,
            precipitation=None,
            wind_speed_10m=None,
            relative_humidity_2m=None,
            provider="Open-Meteo",
            model="ecmwf_aifs025",
        )
    ]
    status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
        records=records,
        requested_variables=[
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
        ],
    )
    assert status == ProviderStatus.NO_VALID_DATA
    assert valid_count == 0
    assert missing_count == 4


def test_assess_dataset_status_available():
    """Verify completely populated dataset within bounds yields AVAILABLE."""
    now = datetime.now(UTC)
    records = [
        ForecastPoint(
            timestamp=now,
            latitude=19.076,
            longitude=72.8777,
            temperature_2m=28.0,
            precipitation=0.0,
            wind_speed_10m=15.0,
            relative_humidity_2m=75.0,
            provider="Open-Meteo",
            model="ecmwf_ifs025",
        )
    ]
    status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
        records=records,
        requested_variables=[
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
        ],
    )
    assert status == ProviderStatus.AVAILABLE
    assert valid_count == 1
    assert missing_count == 0


def test_assess_dataset_status_partial():
    """Verify partially populated dataset yields DEGRADED (not PARTIAL or UNAVAILABLE)."""
    now = datetime.now(UTC)
    records = [
        ForecastPoint(
            timestamp=now,
            latitude=19.076,
            longitude=72.8777,
            temperature_2m=28.0,
            precipitation=None,  # Missing
            wind_speed_10m=15.0,
            relative_humidity_2m=75.0,
            provider="Open-Meteo",
            model="ecmwf_ifs025",
        )
    ]
    status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
        records=records,
        requested_variables=[
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
        ],
    )
    assert status == ProviderStatus.DEGRADED
    assert valid_count == 1
    assert missing_count == 1
