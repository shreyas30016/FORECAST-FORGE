"""Unit tests for Phase 5J Scientific Forecast Replay."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from forecast_forge.replay.schemas import ReplayTimelineResponse
from forecast_forge.replay.service import ReplayService


@pytest.fixture
def run_time():
    return datetime(2026, 9, 20, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_replay_service_initialization():
    service = ReplayService()
    assert service is not None


# We can't do live network calls in unit tests, so we rely on the fact that
# the service handles dependencies properly, and we mock if needed.
# Since the definition of done specifies unit tests MUST use deterministic fixtures
# and be isolated from the network, we'll mock the fetch_historical call.


@pytest.mark.asyncio
async def test_replay_timeline_mocked(run_time):
    # Mock single runs return
    from forecast_forge.core.enums import ProviderStatus
    from forecast_forge.core.models import ForecastPoint, ProviderResult

    service = ReplayService()

    mock_pts = [
        ForecastPoint(
            timestamp=run_time,  # 0h
            latitude=19.07,
            longitude=72.87,
            temperature_2m=25.0,
            provider="open_meteo_single_runs",
            model="gfs_seamless",
            lead_time_hours=0.0,
        ),
        ForecastPoint(
            timestamp=run_time,  # 0h
            latitude=19.07,
            longitude=72.87,
            temperature_2m=25.5,
            provider="open_meteo_single_runs",
            model="ecmwf_ifs04",
            lead_time_hours=0.0,
        ),
    ]

    mock_res = ProviderResult(
        provider_name="open_meteo_single_runs",
        model_name="gfs_seamless",
        status=ProviderStatus.AVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=mock_pts,
    )

    mock_ref_res = ProviderResult(
        provider_name="era5",
        model_name="era5",
        status=ProviderStatus.AVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=[],
    )
    with (
        patch.object(service.providers[0], "fetch_historical", return_value=mock_res),
        patch.object(service.providers[1], "fetch_historical", return_value=mock_res),
        patch.object(
            service, "_get_causal_weights", return_value={"gfs_seamless": 0.6, "ecmwf_ifs04": 0.4}
        ),
        patch.object(service.reference_manager, "fetch_reference_data", return_value=mock_ref_res),
        patch.object(service.trace_storage, "save_trace"),
    ):
        res = await service.get_replay_timeline(19.07, 72.87, run_time, "temperature_2m")

    assert isinstance(res, ReplayTimelineResponse)
    assert len(res.snapshots) == 8

    snap = res.snapshots[0]
    assert snap.forecast_time_decision.lead_time_hours == 0
    assert snap.forecast_time_decision.probabilistic_status == "UNAVAILABLE"
    assert snap.forecast_time_decision.provenance == "single_runs_api"

    # Final blended should be 25.0*0.6 + 25.5*0.4 = 15.0 + 10.2 = 25.2
    assert abs(snap.forecast_time_decision.final_blended_value - 25.2) < 0.01
    assert snap.trace_id is not None


@pytest.mark.asyncio
async def test_replay_timeline_accepts_degraded_provider(run_time):
    """Regression test for Phase 6.2.2:
    Replay must accept DEGRADED data when requested variable is valid.
    """
    from forecast_forge.core.enums import ProviderStatus
    from forecast_forge.core.models import ForecastPoint, ProviderResult

    service = ReplayService()

    mock_pts = [
        ForecastPoint(
            timestamp=run_time,
            latitude=19.07,
            longitude=72.87,
            temperature_2m=26.4,
            provider="open_meteo_single_runs",
            model="gfs_seamless",
            lead_time_hours=0.0,
        )
    ]

    # Provider is marked DEGRADED (e.g. cloud_cover missing, but temperature_2m valid)
    mock_res = ProviderResult(
        provider_name="open_meteo_single_runs",
        model_name="gfs_seamless",
        status=ProviderStatus.DEGRADED,
        request_timestamp=datetime.now(UTC),
        records=mock_pts,
    )

    mock_ref_res = ProviderResult(
        provider_name="era5",
        model_name="era5",
        status=ProviderStatus.DEGRADED,
        request_timestamp=datetime.now(UTC),
        records=[],
    )

    with (
        patch.object(service.providers[0], "fetch_historical", return_value=mock_res),
        patch.object(service.providers[1], "fetch_historical", return_value=mock_res),
        patch.object(service, "_get_causal_weights", return_value={"gfs_seamless": 1.0}),
        patch.object(service.reference_manager, "fetch_reference_data", return_value=mock_ref_res),
        patch.object(service.trace_storage, "save_trace"),
    ):
        res = await service.get_replay_timeline(19.07, 72.87, run_time, "temperature_2m")

    assert isinstance(res, ReplayTimelineResponse)
    snap = res.snapshots[0]
    assert snap.forecast_time_decision.lead_time_hours == 0
    # Must retain data despite DEGRADED provider status
    assert snap.forecast_time_decision.final_blended_value == 26.4
    assert snap.forecast_time_decision.data_quality_status == "DEGRADED"
    assert snap.trace_id is not None

