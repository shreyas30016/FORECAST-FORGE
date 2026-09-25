import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from forecast_forge.core.enums import ProviderStatus
from forecast_forge.core.models import ForecastPoint, ProviderResult
from forecast_forge.replay.registry import ReplayModelRegistry
from forecast_forge.replay.service import ReplayService


@pytest.fixture
def mock_registry_file(tmp_path):
    registry_file = tmp_path / "registry.json"
    data = {
        "artifacts": [
            {
                "model_name": "past_model",
                "artifact_path": "/fake",
                "artifact_hash": "hash1",
                "training_end": "2023-12-31T23:59:59Z",
                "created_at": "2024-01-01T00:00:00Z",
                "model_version": "v1",
            },
            {
                "model_name": "future_model",
                "artifact_path": "/fake2",
                "artifact_hash": "hash2",
                "training_end": "2025-12-31T23:59:59Z",
                "created_at": "2026-01-01T00:00:00Z",
                "model_version": "v2",
            },
        ]
    }
    registry_file.write_text(json.dumps(data))
    return str(registry_file)


def test_artifact_training_end_usable(mock_registry_file):
    registry = ReplayModelRegistry(registry_path=mock_registry_file)
    t0 = datetime(2024, 6, 1, tzinfo=UTC)

    # 1. Past model is usable
    art = registry.get_valid_artifact("past_model", t0)
    assert art is not None
    assert art.model_version == "v1"

    # 2. Future model is rejected
    art2 = registry.get_valid_artifact("future_model", t0)
    assert art2 is None

    # 3. Missing entry
    art3 = registry.get_valid_artifact("nonexistent", t0)
    assert art3 is None


@pytest.mark.asyncio
async def test_replay_temporal_rejection(mock_registry_file):
    # If bust or regime model is rejected, overall status is DEGRADED
    # Let's mock a replay service run
    service = ReplayService()
    service.registry = ReplayModelRegistry(registry_path=mock_registry_file)

    run_time = datetime(2024, 6, 1, tzinfo=UTC)

    # Let's mock providers to return some points
    mock_res = ProviderResult(
        provider_name="open_meteo_single_runs",
        model_name="gfs_seamless",
        status=ProviderStatus.AVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=[
            ForecastPoint(
                timestamp=run_time,
                latitude=19.07,
                longitude=72.87,
                temperature_2m=25.0,
                provider="open_meteo_single_runs",
                model="gfs_seamless",
                initialization_time=run_time,
                lead_time_hours=0.0,
            )
        ],
    )

    mock_ref_res = ProviderResult(
        provider_name="era5",
        model_name="era5",
        status=ProviderStatus.UNAVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=[],
    )

    with (
        patch.object(service.providers[0], "fetch_historical", return_value=mock_res),
        patch.object(service.providers[1], "fetch_historical", return_value=mock_res),
        patch.object(
            service, "_get_causal_weights", return_value={"gfs_seamless": 0.5, "ecmwf_ifs04": 0.5}
        ),
        patch.object(service.reference_manager, "fetch_reference_data", return_value=mock_ref_res),
        patch.object(service.trace_storage, "save_trace"),
    ):
        # The service asks for "mumbai_k3" and "mumbai_bust_model".
        # Since mock_registry_file doesn't have them, they will be rejected (missing).
        res = await service.get_replay_timeline(19.07, 72.87, run_time, "temperature_2m")

        # 8. degraded replay status
        snap = res.snapshots[0]
        assert snap.forecast_time_decision.replay_integrity_status == "DEGRADED"

        # 4. bust model temporal rejection
        assert (
            snap.forecast_time_decision.bust_signal.provenance
            == "MODEL_VERSION_NOT_TEMPORALLY_VALIDATED"
        )

        # 5. regime model temporal rejection
        assert snap.forecast_time_decision.regime is None

        # 6. skill snapshot temporal rejection fallback is used
        # 10. provenance/hash preservation (bust hash is None because it's rejected)
        assert snap.forecast_time_decision.bust_signal.model_hash is None


@pytest.mark.asyncio
async def test_replay_exact_status(tmp_path):
    # Mock an exact registry where the models exist and are valid
    registry_file = tmp_path / "registry.json"
    data = {
        "artifacts": [
            {
                "model_name": "mumbai_k3",
                "artifact_path": "/fake",
                "artifact_hash": "hash_k3",
                "training_end": "2023-12-31T23:59:59Z",
                "created_at": "2024-01-01T00:00:00Z",
                "model_version": "v1",
            },
            {
                "model_name": "mumbai_bust_model",
                "artifact_path": "/fake2",
                "artifact_hash": "hash_bust",
                "training_end": "2023-12-31T23:59:59Z",
                "created_at": "2024-01-01T00:00:00Z",
                "model_version": "v1",
            },
        ]
    }
    registry_file.write_text(json.dumps(data))

    service = ReplayService()
    service.registry = ReplayModelRegistry(registry_path=str(registry_file))

    # We must patch bust_detector and regime_assigner to simulate they are loaded
    class MockRegime:
        def assign_forecast_state(self, feats):
            from forecast_forge.evaluation.regimes.metadata import RegimeAssignment

            return RegimeAssignment(
                regime_id=1, is_valid=True, status="AVAILABLE", model_version="mock_v1"
            )

    class MockBust:
        def predict_signal(self, feats, var):
            return "NORMAL", [], 0.0

    service.regime_assigner = MockRegime()
    service.bust_detector = MockBust()

    run_time = datetime(2024, 6, 1, tzinfo=UTC)
    mock_res = ProviderResult(
        provider_name="open_meteo_single_runs",
        model_name="gfs_seamless",
        status=ProviderStatus.AVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=[
            ForecastPoint(
                timestamp=run_time,
                latitude=19.07,
                longitude=72.87,
                temperature_2m=25.0,
                precipitation=0.0,
                wind_speed_10m=0.0,
                cloud_cover=0.0,
                relative_humidity_2m=50.0,
                provider="open_meteo_single_runs",
                model="gfs_seamless",
                initialization_time=run_time,
                lead_time_hours=0.0,
            )
        ],
    )

    mock_ref_res = ProviderResult(
        provider_name="era5",
        model_name="era5",
        status=ProviderStatus.UNAVAILABLE,
        request_timestamp=datetime.now(UTC),
        records=[],
    )

    with (
        patch.object(service.providers[0], "fetch_historical", return_value=mock_res),
        patch.object(service.providers[1], "fetch_historical", return_value=mock_res),
        patch.object(
            service, "_get_causal_weights", return_value={"gfs_seamless": 0.5, "ecmwf_ifs04": 0.5}
        ),
        patch.object(service.reference_manager, "fetch_reference_data", return_value=mock_ref_res),
        patch.object(service.trace_storage, "save_trace"),
    ):
        res = await service.get_replay_timeline(19.07, 72.87, run_time, "temperature_2m")

        # 7. exact replay status
        snap = res.snapshots[0]
        assert snap.forecast_time_decision.replay_integrity_status == "EXACT"

        # 10. provenance/hash preservation
        assert snap.forecast_time_decision.regime.model_hash == "hash_k3"
        assert snap.forecast_time_decision.bust_signal.model_hash == "hash_bust"
        assert snap.forecast_time_decision.bust_signal.signal == "NORMAL"
