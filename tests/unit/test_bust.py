"""Tests for Forecast-Bust Intelligence (Phase 5I)."""

import numpy as np
import pandas as pd

from forecast_forge.evaluation.bust.detector import ForecastBustDetector
from forecast_forge.evaluation.bust.schemas import ForecastBustSignal


def test_bust_detector_training():
    """Test that the detector trains thresholds properly and avoids leakage."""
    # Create deterministic mock data
    np.random.seed(42)
    records = []

    for vt in pd.date_range("2026-01-01", periods=100, freq="D"):
        # Lead 24h
        target_24 = 25.0 + np.random.normal(0, 1)
        ref_24 = target_24 + np.random.normal(0, 0.5)
        records.append(
            {
                "valid_time": vt,
                "lead_time_hours": 24,
                "target_forecast": target_24,
                "ref_temperature_2m": ref_24,
                "temperature_2m": target_24,
                "model_spread": 0.5,
                "valid_member_count": 31,
                "regime_id": 1,
                "precipitation": 0,
                "wind_speed_10m": 5,
            }
        )

        # Lead 120h (higher variance)
        target_120 = 25.0 + np.random.normal(0, 2)
        ref_120 = target_120 + np.random.normal(0, 2.5)
        records.append(
            {
                "valid_time": vt,
                "lead_time_hours": 120,
                "target_forecast": target_120,
                "ref_temperature_2m": ref_120,
                "temperature_2m": target_120,
                "model_spread": 2.5,
                "valid_member_count": 31,
                "regime_id": 2,
                "precipitation": 0,
                "wind_speed_10m": 5,
            }
        )

    df = pd.DataFrame(records)

    # Train test split
    train_df = df.iloc[:100]
    test_df = df.iloc[100:]

    detector = ForecastBustDetector()
    detector.fit(train_df, "temperature_2m", quantile=0.90)

    # Assert thresholds created per lead time
    assert ("temperature_2m", 24) in detector.thresholds
    assert ("temperature_2m", 120) in detector.thresholds

    # Assert 120h threshold is strictly higher because of higher error variance
    assert (
        detector.thresholds[("temperature_2m", 120)] > detector.thresholds[("temperature_2m", 24)]
    )

    # Test prediction
    signal, factors, thresh = detector.predict_signal(test_df.iloc[0].to_dict(), "temperature_2m")
    assert signal in ["NORMAL", "ELEVATED"]
    assert (
        thresh == detector.thresholds[("temperature_2m", 24)]
    )  # index 100 is lead 24 because of interlacing
    assert len(factors) <= 3


def test_bust_signal_schema():
    """Test schema validation."""
    signal = ForecastBustSignal(
        signal="ELEVATED",
        variable="temperature_2m",
        lead_time_hours=72.0,
        bust_threshold=1.5,
        historical_error_quantile=0.9,
        primary_factors=[],
        status="AVAILABLE",
        provenance="Test",
    )

    assert signal.signal == "ELEVATED"
    assert signal.variable == "temperature_2m"
    assert signal.lead_time_hours == 72.0
