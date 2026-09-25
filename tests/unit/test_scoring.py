"""Tests for scoring engine."""

import pandas as pd

from forecast_forge.evaluation.scoring import generate_model_scores, normalize_scores


def test_scoring_flow():
    df = pd.DataFrame(
        {
            "model": ["test_model"] * 5,
            "lead_time_bucket": ["0-6h"] * 5,
            "temperature_2m": [1, 2, 3, 4, 5],
            "ref_temperature_2m": [1, 2, 3, 4, 5],
        }
    )

    scores = generate_model_scores(df, "test_model", "temperature_2m", min_samples=3)
    assert len(scores) == 1
    assert scores[0].is_valid
    assert scores[0].metrics.rmse == 0.0

    normalized = normalize_scores(scores)
    assert normalized[0].reliability_score == 50.0  # Only one model -> equal max/min
