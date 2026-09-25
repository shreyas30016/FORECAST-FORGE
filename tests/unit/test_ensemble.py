"""Tests for ensemble logic."""

from datetime import datetime

import pandas as pd

from forecast_forge.ensemble.adaptive import AdaptiveEnsembleModel
from forecast_forge.ensemble.baseline import (
    calculate_equal_weight_ensemble,
    calculate_inverse_error_ensemble,
)
from forecast_forge.ensemble.engine import generate_ensemble_forecast
from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast
from forecast_forge.ensemble.uncertainty import calculate_uncertainty


def test_equal_weight_baseline():
    forecasts = [
        ModelForecast(model="ifs", value=10.0, is_valid=True),
        ModelForecast(model="gfs", value=20.0, is_valid=True),
        ModelForecast(model="aifs", value=None, is_valid=False, status="UNAVAILABLE"),
    ]
    val = calculate_equal_weight_ensemble(forecasts)
    assert val == 15.0


def test_inverse_error_baseline():
    forecasts = [
        ModelForecast(model="ifs", value=10.0, is_valid=True),
        ModelForecast(model="gfs", value=20.0, is_valid=True),
        ModelForecast(model="aifs", value=None, is_valid=False),
    ]
    weights = [
        EnsembleWeight(model="ifs", weight=0.8),
        EnsembleWeight(model="gfs", weight=0.2),
        EnsembleWeight(model="aifs", weight=0.0),
    ]
    val = calculate_inverse_error_ensemble(forecasts, weights)
    assert val == 12.0


def test_uncertainty_spread():
    forecasts = [
        ModelForecast(model="ifs", value=10.0, is_valid=True),
        ModelForecast(model="gfs", value=10.0, is_valid=True),
        ModelForecast(model="aifs", value=10.0, is_valid=True),
    ]
    unc = calculate_uncertainty(forecasts, 3)
    assert unc.spread == 0.0
    assert unc.data_quality_indicator == "HIGH"
    assert unc.valid_model_count == 3


def test_adaptive_feature_construction():
    # Test Config D
    df = pd.DataFrame(
        {
            "valid_time": pd.date_range("2023-01-01", periods=3, freq="h"),
            "ifs_temp": [1, 2, 3],
            "gfs_temp": [1.1, 2.1, 3.1],
            "ifs_trailing_mae": [0.1, 0.2, 0.3],
            "gfs_trailing_mae": [0.4, 0.5, 0.6],
        }
    )

    model = AdaptiveEnsembleModel(variable="temp", alpha=1.0, feature_config="D")
    feats = model._extract_features(df, ["ifs", "gfs"])

    assert "ifs" in feats.columns
    assert "gfs" in feats.columns
    assert "hour_sin" in feats.columns
    assert "model_spread" in feats.columns
    assert "ifs_historical_skill" in feats.columns
    assert feats.loc[0, "ifs_historical_skill"] == 0.1


def test_adaptive_ensemble_fit_predict():
    # Construct a small df
    df = pd.DataFrame(
        {
            "valid_time": pd.date_range("2023-01-01", periods=10, freq="h"),
            "ifs_temp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "gfs_temp": [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1],
            "ref_temp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # IFS is perfect
        }
    )

    model = AdaptiveEnsembleModel(
        variable="temp", alpha=0.0, feature_config="B"
    )  # no reg to easily see ifs wins
    model.fit(df, ["ifs", "gfs"])

    assert model.is_fitted
    preds = model.predict(df)
    assert len(preds) == 10

    # IFS should heavily dominate weight
    weights = model.get_dynamic_weights()
    w_ifs = next(w.weight for w in weights if w.model == "ifs")
    w_gfs = next(w.weight for w in weights if w.model == "gfs")
    assert w_ifs > w_gfs  # since IFS perfectly matches ref_temp


def test_engine_orchestrator():
    forecasts = [
        ModelForecast(model="ifs", value=10.0, is_valid=True),
        ModelForecast(model="gfs", value=20.0, is_valid=True),
        ModelForecast(model="aifs", value=None, is_valid=False, status="NO_VALID_DATA"),
    ]
    res = generate_ensemble_forecast(
        location_name="Test",
        variable="temp",
        valid_time=datetime.now(),
        forecasts=forecasts,
        expected_total_models=3,
    )

    assert res.equal_weight_forecast == 15.0
    assert res.uncertainty.valid_model_count == 2
    assert res.uncertainty.data_quality_indicator == "PARTIAL"
    assert "aifs" in res.explanation.dropped_models

    # Null forecast display explicitly verified
    aifs_fcst = next(f for f in res.model_forecasts if f.model == "aifs")
    assert aifs_fcst.value is None
    assert aifs_fcst.status == "NO_VALID_DATA"


def test_explanation_generation_deterministic():
    """Verify deterministic explanation with runtime percentages and explicit AIFS exclusion."""
    from forecast_forge.ensemble.explanations import generate_explanation

    forecasts = [
        ModelForecast(model="ecmwf_ifs025", value=31.4, is_valid=True),
        ModelForecast(model="gfs_seamless", value=30.2, is_valid=True),
        ModelForecast(model="ecmwf_aifs025", value=None, is_valid=False, status="UNAVAILABLE"),
    ]
    weights = [
        EnsembleWeight(model="ecmwf_ifs025", weight=0.729),
        EnsembleWeight(model="gfs_seamless", weight=0.271),
        EnsembleWeight(model="ecmwf_aifs025", weight=0.0),
    ]

    expl = generate_explanation(forecasts, weights, variable="temperature_2m")

    assert "ECMWF IFS" in expl.reasoning
    assert "73% weight to ECMWF IFS" in expl.reasoning
    assert "27% weight to NOAA GFS" in expl.reasoning
    assert "ECMWF AIFS excluded because valid forecast data was unavailable" in expl.reasoning
    assert "ecmwf_aifs025" in expl.dropped_models


def test_timestamp_consistency():
    """Verify valid_time remains identical across all ensemble components."""
    fixed_time = datetime(2026, 9, 24, 12, 0, 0)
    forecasts = [
        ModelForecast(model="ecmwf_ifs025", value=25.0, is_valid=True),
        ModelForecast(model="gfs_seamless", value=26.0, is_valid=True),
    ]
    res = generate_ensemble_forecast(
        location_name="Mumbai",
        variable="temperature_2m",
        valid_time=fixed_time,
        forecasts=forecasts,
    )
    assert res.valid_time == fixed_time
