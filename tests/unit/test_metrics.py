"""Tests for the metrics engine."""

import numpy as np
import pandas as pd

from forecast_forge.evaluation.metrics import calculate_metrics


def test_metrics_perfect_prediction():
    preds = pd.Series([1.0, 2.0, 3.0])
    obs = pd.Series([1.0, 2.0, 3.0])
    res = calculate_metrics(preds, obs)
    assert res.mae == 0.0
    assert res.rmse == 0.0
    assert res.mean_bias == 0.0
    assert res.valid_samples == 3
    assert res.missing_samples == 0


def test_metrics_constant_error():
    preds = pd.Series([2.0, 3.0, 4.0])
    obs = pd.Series([1.0, 2.0, 3.0])
    res = calculate_metrics(preds, obs)
    assert res.mae == 1.0
    assert res.rmse == 1.0
    assert res.mean_bias == 1.0


def test_metrics_negative_bias():
    preds = pd.Series([0.0, 1.0, 2.0])
    obs = pd.Series([1.0, 2.0, 3.0])
    res = calculate_metrics(preds, obs)
    assert res.mae == 1.0
    assert res.rmse == 1.0
    assert res.mean_bias == -1.0


def test_metrics_nan_handling():
    preds = pd.Series([1.0, np.nan, 3.0])
    obs = pd.Series([1.0, 2.0, np.nan])
    res = calculate_metrics(preds, obs)
    assert res.valid_samples == 1
    assert res.missing_samples == 2
    assert res.mae == 0.0


def test_metrics_empty():
    res = calculate_metrics(pd.Series(dtype=float), pd.Series(dtype=float))
    assert res.valid_samples == 0
    assert res.mae is None
