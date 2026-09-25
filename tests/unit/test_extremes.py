"""Unit tests for extremes guidance service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.ensemble.schemas import EventProbabilityResult, ProbabilisticForecast
from forecast_forge.extremes.schemas import EventDefinition
from forecast_forge.extremes.service import ExtremesService


@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    regime = MagicMock()
    regime.regime_id = 1
    regime.description = "Mock Regime"
    regime.sample_count = 100
    pipeline.regimes = [regime]
    return pipeline


@pytest.fixture
def mock_assigner():
    assigner = MagicMock()
    assignment = MagicMock()
    assignment.is_valid = True
    assignment.regime_id = 1
    assigner.assign_forecast_state.return_value = assignment
    return assigner


@pytest.fixture
def mock_adapter():
    with patch("forecast_forge.extremes.service.OpenMeteoEnsembleAdapter") as mock:
        adapter_instance = mock.return_value
        yield adapter_instance


@pytest.mark.asyncio
async def test_extremes_service_basic_guidance(mock_adapter, mock_assigner, mock_pipeline):
    # Setup mock adapter to return a specific probability distribution
    prob_fcst = ProbabilisticForecast(
        model="gfs_seamless",
        variable="temperature_2m",
        latitude=19.0,
        longitude=72.0,
        lead_time_hours=72,
        valid_time=datetime.now(UTC),
        member_count=31,
        valid_member_count=31,
        mean=36.0,
        median=36.0,
        p10=30.0,
        p25=32.0,
        p50=36.0,
        p75=38.0,
        p90=40.0,
        status="AVAILABLE",
        provenance="Test_Provenance",
    )

    # 1. Extreme Temperature (>= 35.0) -> probability 1.0
    ep1 = EventProbabilityResult(
        variable="temperature_2m",
        operator=">=",
        threshold=35.0,
        probability=1.0,
        valid_member_count=31,
        status="AVAILABLE",
    )

    # 2. Heavy Rain (>= 25.0) -> probability 0.0
    ep2 = EventProbabilityResult(
        variable="precipitation",
        operator=">=",
        threshold=25.0,
        probability=0.0,
        valid_member_count=31,
        status="AVAILABLE",
    )

    # 3. High Wind (>= 50.0) -> probability 0.5
    ep3 = EventProbabilityResult(
        variable="wind_speed_10m",
        operator=">=",
        threshold=50.0,
        probability=0.5,
        valid_member_count=31,
        status="AVAILABLE",
    )

    mock_adapter.fetch_probabilistic_forecast = AsyncMock(
        return_value={
            WeatherVariable.TEMPERATURE_2M: [(prob_fcst, [ep1])],
            WeatherVariable.PRECIPITATION: [(prob_fcst, [ep2])],
            WeatherVariable.WIND_SPEED_10M: [(prob_fcst, [ep3])],
        }
    )

    # Initialize service with mock assigner
    service = ExtremesService()
    service.pipeline = mock_pipeline
    service.regime_assigner = mock_assigner

    results = await service.get_guidance(
        latitude=19.0,
        longitude=72.0,
        location_name="Test",
        lead_time_hours=72,
        model="gfs_seamless",
    )

    assert len(results) == 3

    # Check Temp
    temp_res = next(r for r in results if r.event_type == "Extreme Temperature")
    assert temp_res.probability == 1.0
    assert temp_res.status == "AVAILABLE"
    assert temp_res.provenance == "Test_Provenance"
    assert temp_res.ensemble_member_count == 31
    assert temp_res.valid_member_count == 31
    assert temp_res.active_models == ["gfs_seamless"]
    assert temp_res.regime is not None
    assert temp_res.regime.regime_description == "Mock Regime"

    # Check Rain
    rain_res = next(r for r in results if r.event_type == "Heavy Rain")
    assert rain_res.probability == 0.0

    # Check Wind
    wind_res = next(r for r in results if r.event_type == "High Wind")
    assert wind_res.probability == 0.5


@pytest.mark.asyncio
async def test_extremes_unavailable_model(mock_adapter):
    mock_adapter.fetch_probabilistic_forecast = AsyncMock(side_effect=Exception("API Error"))
    service = ExtremesService()
    results = await service.get_guidance(
        latitude=19.0,
        longitude=72.0,
        location_name="Test",
        lead_time_hours=72,
        model="gfs_seamless",
    )
    assert len(results) == 3
    for res in results:
        assert res.status == "UNAVAILABLE"
        assert res.probability is None


@pytest.mark.asyncio
async def test_extremes_insufficient_members(mock_adapter):
    prob_fcst = ProbabilisticForecast(
        model="gfs_seamless",
        variable="temperature_2m",
        latitude=19.0,
        longitude=72.0,
        lead_time_hours=72,
        valid_time=datetime.now(UTC),
        member_count=31,
        valid_member_count=0,  # 0 members!
        mean=36.0,
        median=36.0,
        p10=30.0,
        p25=32.0,
        p50=36.0,
        p75=38.0,
        p90=40.0,
        status="INSUFFICIENT_DATA",
        provenance="Test",
    )
    ep1 = EventProbabilityResult(
        variable="temperature_2m",
        operator=">=",
        threshold=35.0,
        probability=None,
        valid_member_count=0,
        status="INSUFFICIENT_DATA",
    )
    mock_adapter.fetch_probabilistic_forecast = AsyncMock(
        return_value={
            WeatherVariable.TEMPERATURE_2M: [(prob_fcst, [ep1])],
        }
    )
    service = ExtremesService()
    # Override events to just test temp
    service.events = [
        EventDefinition(
            event_type="Extreme Temperature",
            variable="temperature_2m",
            operator=">=",
            threshold=35.0,
            unit="C",
        )
    ]
    results = await service.get_guidance(19.0, 72.0, "Test", 72, "gfs_seamless")
    assert results[0].status == "INSUFFICIENT_DATA"
    assert results[0].probability is None


@pytest.mark.asyncio
@patch("forecast_forge.extremes.service.OpenMeteoEnsembleAdapter")
async def test_extremes_model_separation_aifs(mock_adapter_class):
    mock_adapter_instance = mock_adapter_class.return_value
    mock_adapter_instance.fetch_probabilistic_forecast = AsyncMock(return_value={})
    service = ExtremesService()
    await service.get_guidance(19.0, 72.0, "Test", 72, "ecmwf_aifs025")
    mock_adapter_class.assert_called_with(model_name="ecmwf_aifs025", member_prefix="ecmwf_aifs025")
