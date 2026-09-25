"""Tests for model weighting."""

import pytest

from forecast_forge.evaluation.schemas import MetricResult, ModelScore
from forecast_forge.evaluation.weighting import calculate_weights


def build_score(model, rmse, valid):
    return ModelScore(
        model=model,
        variable="temp",
        lead_time_bucket="0-6h",
        is_valid=valid,
        metrics=MetricResult(rmse=rmse, valid_samples=10, missing_samples=0),
    )


def test_weights_sum_to_one():
    s1 = build_score("m1", 1.0, True)
    s2 = build_score("m2", 2.0, True)
    weights = calculate_weights([s1, s2])
    assert sum(w.weight for w in weights) == pytest.approx(1.0)


def test_missing_model_zero_weight():
    s1 = build_score("m1", 1.0, True)
    s2 = build_score("aifs", None, False)
    weights = calculate_weights([s1, s2])
    w_aifs = next(w for w in weights if w.model == "aifs")
    assert w_aifs.weight == 0.0


def test_zero_error_protection():
    s1 = build_score("m1", 0.0, True)
    s2 = build_score("m2", 1.0, True)
    weights = calculate_weights([s1, s2])
    # m1 should have nearly 100% weight due to epsilon protection
    w_m1 = next(w for w in weights if w.model == "m1")
    assert w_m1.weight > 0.99
