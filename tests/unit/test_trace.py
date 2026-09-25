"""Unit tests for Phase 5K Decision Trace & Scientific Provenance."""

import uuid
from datetime import UTC, datetime

import pytest

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.replay.schemas import (
    ForecastTimeDecision,
    LaterVerification,
    ReplayBustSnapshot,
    ReplayRegimeSnapshot,
    ReplaySnapshot,
)
from forecast_forge.trace.builder import TraceBuilder
from forecast_forge.trace.storage import TraceStorage


@pytest.fixture
def mock_replay_snapshot():
    run_time = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
    vt = datetime(2026, 9, 23, 0, 0, tzinfo=UTC)
    decision = ForecastTimeDecision(
        initialization_time=run_time,
        valid_time=vt,
        lead_time_hours=72,
        model_forecasts={"gfs_seamless": 25.0, "ecmwf_ifs04": 26.0},
        model_availability={"gfs_seamless": "AVAILABLE", "ecmwf_ifs04": "AVAILABLE"},
        replay_integrity_status="EXACT",
        spatial_weights={"gfs_seamless": 0.5, "ecmwf_ifs04": 0.5},
        lead_time_weights={},
        final_blended_value=25.5,
        regime=ReplayRegimeSnapshot(
            regime_id=2,
            regime_model_version="k3_kmeans_v1",
            feature_snapshot={"temperature_2m": 25.0},
            assignment_provenance="forecast_time_features",
            causal_cutoff=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
            model_hash="dummyhash",
        ),
        probabilistic_summary={"reason": "Unavailable API"},
        probabilistic_status="UNAVAILABLE",
        extreme_guidance=[],
        bust_signal=ReplayBustSnapshot(
            signal="NORMAL",
            score=0.1,
            model_version="bust_detector_v1",
            provenance="forecast_time_features",
            causal_cutoff=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
            model_hash="busthash",
        ),
        provenance="single_runs_api",
        data_quality_status="AVAILABLE",
    )

    return ReplaySnapshot(
        replay_id=str(uuid.uuid4()),
        latitude=19.07,
        longitude=72.87,
        variable="temperature_2m",
        run=run_time,
        forecast_time_decision=decision,
        later_verification=LaterVerification(
            valid_time=vt, reference_value=25.6, realized_error=0.1, reference_source="ERA5"
        ),
    )


def test_trace_builder_exact(mock_replay_snapshot):
    trace = TraceBuilder.from_replay_snapshot(mock_replay_snapshot)

    assert trace.decision_integrity == "EXACT"
    assert trace.forecast.value == 25.5
    assert trace.forecast.source == "single_runs_api"
    assert trace.regime.regime_id == 2
    assert trace.regime.causal_cutoff == datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)
    assert trace.probabilistic.status == "UNAVAILABLE"
    assert len(trace.weights) == 2
    assert trace.bust_signal.signal == "NORMAL"
    assert trace.verification.status == "AVAILABLE"
    assert trace.verification.error == 0.1


def test_trace_storage(tmp_path, mock_replay_snapshot):
    cache_path = tmp_path / "test_trace_cache"
    storage = TraceStorage(cache_dir=str(cache_path))

    trace = TraceBuilder.from_replay_snapshot(mock_replay_snapshot)

    storage.save_trace(trace, mock_replay_snapshot.replay_id)

    # Test retrieve by ID
    retrieved = storage.get_trace(trace.trace_id)
    assert retrieved is not None
    assert retrieved.trace_id == trace.trace_id

    # Test retrieve by context
    found = storage.find_trace(
        latitude=19.07,
        longitude=72.87,
        valid_time=datetime(2026, 9, 23, 0, 0, tzinfo=UTC),
        lead_time_hours=72,
        variable=WeatherVariable.TEMPERATURE_2M,
    )
    assert found is not None
    assert found.trace_id == trace.trace_id

    # Test retrieve by replay ID
    traces = storage.find_by_replay(mock_replay_snapshot.replay_id)
    assert len(traces) == 1
    assert traces[0].trace_id == trace.trace_id
