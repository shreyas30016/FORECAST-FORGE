"""Unit tests for the probabilistic ensemble engine."""

import pytest

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.ensemble.schemas import EventProbabilityRequest
from forecast_forge.providers.open_meteo.ensemble import OpenMeteoEnsembleAdapter


@pytest.fixture
def mock_open_meteo_ensemble_response():
    """Mock an Open-Meteo ensemble JSON response."""
    return {
        "hourly": {
            "time": [
                "2026-09-25T00:00",
                "2026-09-25T01:00",
                "2026-09-25T02:00",
            ],
            "temperature_2m_member01_ncep_gefs_seamless": [20.0, 21.0, 22.0],
            "temperature_2m_member02_ncep_gefs_seamless": [20.5, 21.5, 22.5],
            "temperature_2m_member03_ncep_gefs_seamless": [19.5, 20.5, 21.5],
            "temperature_2m_member04_ncep_gefs_seamless": [21.0, 22.0, 23.0],
            "temperature_2m_member05_ncep_gefs_seamless": [None, 21.2, 22.2],  # Test nulls
            "precipitation_member01_ncep_gefs_seamless": [0.0, 5.0, 10.0],
            "precipitation_member02_ncep_gefs_seamless": [0.0, 0.0, 15.0],
            "precipitation_member03_ncep_gefs_seamless": [1.0, 2.0, 3.0],
        }
    }


def test_open_meteo_ensemble_adapter_parsing(mock_open_meteo_ensemble_response):
    """Test parsing logic for quantiles and member validation."""
    adapter = OpenMeteoEnsembleAdapter(
        model_name="gfs_seamless", member_prefix="ncep_gefs_seamless"
    )

    loc = Location(name="Test", latitude=0.0, longitude=0.0)
    req = ForecastRequest(
        location=loc, variables=[WeatherVariable.TEMPERATURE_2M, WeatherVariable.PRECIPITATION]
    )

    event_req = EventProbabilityRequest(variable="precipitation", operator=">=", threshold=5.0)

    results = adapter._parse_ensemble_response(mock_open_meteo_ensemble_response, req, [event_req])

    assert WeatherVariable.TEMPERATURE_2M in results
    assert WeatherVariable.PRECIPITATION in results

    temp_results = results[WeatherVariable.TEMPERATURE_2M]
    assert len(temp_results) == 3

    # First timestep: [20.0, 20.5, 19.5, 21.0] -> null ignored
    prob, ev = temp_results[0]
    assert prob.valid_member_count == 4
    assert prob.mean == pytest.approx(20.25)

    # Second timestep: all 5 are valid
    prob, ev = temp_results[1]
    assert prob.valid_member_count == 5

    # Check probabilities for precipitation
    precip_results = results[WeatherVariable.PRECIPITATION]
    prob, ev = precip_results[1]  # T=1
    assert prob.valid_member_count == 3
    assert len(ev) == 1
    # values: [5.0, 0.0, 2.0], threshold=5.0, >= -> 1/3
    assert ev[0].probability == pytest.approx(1 / 3)

    prob, ev = precip_results[2]  # T=2
    # values: [10.0, 15.0, 3.0], threshold=5.0, >= -> 2/3
    assert ev[0].probability == pytest.approx(2 / 3)


def test_insufficient_data(mock_open_meteo_ensemble_response):
    """Test when no members are valid."""
    # Wipe out data for hour 0 precip
    mock_open_meteo_ensemble_response["hourly"]["precipitation_member01_ncep_gefs_seamless"][0] = (
        None
    )
    mock_open_meteo_ensemble_response["hourly"]["precipitation_member02_ncep_gefs_seamless"][0] = (
        None
    )
    mock_open_meteo_ensemble_response["hourly"]["precipitation_member03_ncep_gefs_seamless"][0] = (
        None
    )

    adapter = OpenMeteoEnsembleAdapter(
        model_name="gfs_seamless", member_prefix="ncep_gefs_seamless"
    )
    req = ForecastRequest(
        location=Location(latitude=0, longitude=0), variables=[WeatherVariable.PRECIPITATION]
    )
    results = adapter._parse_ensemble_response(mock_open_meteo_ensemble_response, req)

    prob, ev = results[WeatherVariable.PRECIPITATION][0]
    assert prob.valid_member_count == 0
    assert prob.status == "INSUFFICIENT_DATA"
    assert prob.mean is None
    assert prob.p50 is None
