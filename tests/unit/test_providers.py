"""Unit tests for weather model provider adapters, HTTP handling, and status mapping."""

from unittest.mock import AsyncMock

import pytest

from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.exceptions import (
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.orchestrator.service import ForecastOrchestrator
from forecast_forge.providers.http_client import ResilientHTTPClient
from forecast_forge.providers.open_meteo.aifs import ECMWFAIFSProvider
from forecast_forge.providers.open_meteo.gfs import NOAAGFSProvider
from forecast_forge.providers.open_meteo.ifs import ECMWFIFSProvider


@pytest.fixture
def test_location() -> Location:
    return Location(latitude=19.076, longitude=72.8777, name="Mumbai")


@pytest.fixture
def test_request(test_location: Location) -> ForecastRequest:
    return ForecastRequest(
        location=test_location,
        variables=[
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
        ],
        forecast_days=1,
    )


@pytest.fixture
def mock_ifs_payload() -> dict:
    return {
        "latitude": 19.076,
        "longitude": 72.8777,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": ["2026-09-22T00:00", "2026-09-22T01:00"],
            "temperature_2m": [26.5, 26.2],
            "relative_humidity_2m": [82.0, 84.0],
            "precipitation": [0.0, 0.5],
            "wind_speed_10m": [12.0, 14.0],
        },
    }


@pytest.fixture
def mock_gfs_payload() -> dict:
    return {
        "latitude": 19.076,
        "longitude": 72.8777,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": ["2026-09-22T00:00", "2026-09-22T01:00"],
            "temperature_2m": [27.0, 26.8],
            "relative_humidity_2m": [80.0, 81.0],
            "precipitation": [0.0, 0.0],
            "wind_speed_10m": [11.0, 13.0],
        },
    }


@pytest.fixture
def mock_aifs_null_payload() -> dict:
    """Simulates real Open-Meteo AIFS response with timestamps but null weather fields."""
    return {
        "latitude": 19.076,
        "longitude": 72.8777,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": ["2026-09-22T00:00", "2026-09-22T01:00"],
            "temperature_2m": [None, None],
            "relative_humidity_2m": [None, None],
            "precipitation": [None, None],
            "wind_speed_10m": [None, None],
        },
    }


@pytest.mark.asyncio
async def test_successful_ifs_response(test_request: ForecastRequest, mock_ifs_payload: dict):
    """Verify ECMWF IFS provider parses payload into valid canonical records."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.return_value = (200, mock_ifs_payload, 45.0)

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.AVAILABLE
    assert result.total_records == 2
    assert result.valid_records == 2
    assert result.missing_variables_count == 0
    assert result.response_status_code == 200
    assert len(result.records) == 2
    assert result.records[0].temperature_2m == 26.5
    assert result.records[0].model == "ecmwf_ifs025"


@pytest.mark.asyncio
async def test_successful_gfs_response(test_request: ForecastRequest, mock_gfs_payload: dict):
    """Verify NOAA GFS provider parses payload into valid canonical records."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.return_value = (200, mock_gfs_payload, 50.0)

    provider = NOAAGFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.AVAILABLE
    assert result.total_records == 2
    assert result.valid_records == 2
    assert result.records[0].temperature_2m == 27.0
    assert result.records[0].model == "gfs_seamless"


@pytest.mark.asyncio
async def test_aifs_null_response_never_fabricated(
    test_request: ForecastRequest, mock_aifs_null_payload: dict
):
    """CRITICAL: Verify AIFS null payload is flagged NO_VALID_DATA and NEVER fabricated."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.return_value = (200, mock_aifs_null_payload, 40.0)

    provider = ECMWFAIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    # Status must strictly be NO_VALID_DATA (HTTP 200 but all values null)
    assert result.status == ProviderStatus.NO_VALID_DATA
    assert result.total_records == 2
    assert result.valid_records == 0
    assert result.missing_variables_count == 8  # 2 timestamps * 4 variables

    # Values must remain None, never substituted or faked
    for record in result.records:
        assert record.temperature_2m is None
        assert record.precipitation is None
        assert record.wind_speed_10m is None
        assert record.relative_humidity_2m is None
        assert record.model == "ecmwf_aifs025"


@pytest.mark.asyncio
async def test_malformed_response_missing_hourly(test_request: ForecastRequest):
    """Verify responses missing the 'hourly' key result in NO_VALID_DATA."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.return_value = (200, {"error": True, "reason": "Bad model"}, 30.0)

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.NO_VALID_DATA
    assert result.total_records == 0
    assert "Provider response error" in (result.error_message or "")


@pytest.mark.asyncio
async def test_http_400_client_error(test_request: ForecastRequest):
    """Verify HTTP 400 maps to ERROR status with response status code 400."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.side_effect = ProviderHTTPError(
        message="HTTP 400 Bad Request",
        provider_name="Open-Meteo",
        status_code=400,
    )

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.ERROR
    assert result.response_status_code == 400


@pytest.mark.asyncio
async def test_http_429_rate_limited(test_request: ForecastRequest):
    """Verify HTTP 429 maps to RATE_LIMITED status."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.side_effect = ProviderRateLimitError(
        message="HTTP 429 Rate Limited",
        provider_name="Open-Meteo",
    )

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.RATE_LIMITED
    assert result.response_status_code == 429


@pytest.mark.asyncio
async def test_provider_timeout(test_request: ForecastRequest):
    """Verify timeout maps to UNAVAILABLE status."""
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.side_effect = ProviderTimeoutError(
        message="Timeout after retries",
        provider_name="Open-Meteo",
    )

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.UNAVAILABLE
    assert "Timeout after retries" in (result.error_message or "")


@pytest.mark.asyncio
async def test_missing_variables_yields_partial_status(test_request: ForecastRequest):
    """Verify response missing one requested variable results in DEGRADED status."""
    payload_missing_wind = {
        "latitude": 19.076,
        "longitude": 72.8777,
        "hourly_units": {"time": "iso8601"},
        "hourly": {
            "time": ["2026-09-22T00:00"],
            "temperature_2m": [26.0],
            "relative_humidity_2m": [80.0],
            "precipitation": [0.0],
            "wind_speed_10m": [None],  # Missing
        },
    }
    mock_client = AsyncMock(spec=ResilientHTTPClient)
    mock_client.get_json.return_value = (200, payload_missing_wind, 25.0)

    provider = ECMWFIFSProvider(http_client=mock_client)
    result = await provider.fetch_forecast(test_request)

    assert result.status == ProviderStatus.DEGRADED
    assert result.total_records == 1
    assert result.valid_records == 1
    assert result.missing_variables_count == 1


@pytest.mark.asyncio
async def test_orchestrator_fault_isolation(
    test_request: ForecastRequest,
    mock_ifs_payload: dict,
    mock_gfs_payload: dict,
    mock_aifs_null_payload: dict,
):
    """Verify orchestrator concurrently fetches all models and isolates AIFS nulls from IFS/GFS."""
    client_ifs = AsyncMock(spec=ResilientHTTPClient)
    client_ifs.get_json.return_value = (200, mock_ifs_payload, 30.0)

    client_gfs = AsyncMock(spec=ResilientHTTPClient)
    client_gfs.get_json.return_value = (200, mock_gfs_payload, 35.0)

    client_aifs = AsyncMock(spec=ResilientHTTPClient)
    client_aifs.get_json.return_value = (200, mock_aifs_null_payload, 25.0)

    ifs_prov = ECMWFIFSProvider(http_client=client_ifs)
    gfs_prov = NOAAGFSProvider(http_client=client_gfs)
    aifs_prov = ECMWFAIFSProvider(http_client=client_aifs)

    orchestrator = ForecastOrchestrator(providers=[ifs_prov, gfs_prov, aifs_prov])
    results = await orchestrator.fetch_all(test_request)

    assert len(results) == 3
    assert results["ecmwf_ifs025"].status == ProviderStatus.AVAILABLE
    assert results["gfs_seamless"].status == ProviderStatus.AVAILABLE
    assert results["ecmwf_aifs025"].status == ProviderStatus.NO_VALID_DATA
