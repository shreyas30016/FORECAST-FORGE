"""Model reliability scoring."""

import pandas as pd

from forecast_forge.evaluation.metrics import calculate_metrics
from forecast_forge.evaluation.schemas import ModelScore


def generate_model_scores(
    df: pd.DataFrame, model: str, variable: str, min_samples: int = 5
) -> list[ModelScore]:
    """
    Generate scores for a specific model and variable across all available lead-time buckets.
    """
    scores = []

    if df.empty or "model" not in df.columns or "lead_time_bucket" not in df.columns:
        return scores

    model_df = df[df["model"] == model]
    if model_df.empty:
        return scores

    ref_col = f"ref_{variable}"
    if variable not in model_df.columns or ref_col not in model_df.columns:
        return scores

    for bucket, group in model_df.groupby("lead_time_bucket"):
        metrics = calculate_metrics(group[variable], group[ref_col])
        is_valid = metrics.valid_samples >= min_samples

        score = ModelScore(
            model=model,
            variable=variable,
            lead_time_bucket=str(bucket),
            metrics=metrics,
            is_valid=is_valid,
            reliability_score=None,
            normalized_error=None,
        )
        scores.append(score)

    return scores


def normalize_scores(scores: list[ModelScore]) -> list[ModelScore]:
    """
    Normalize errors across models in the same bucket and calculate 0-100 reliability.
    """
    # Group by bucket
    bucket_map = {}
    for s in scores:
        bucket_map.setdefault(s.lead_time_bucket, []).append(s)

    for _bucket, bucket_scores in bucket_map.items():
        valid_scores = [s for s in bucket_scores if s.is_valid and s.metrics.rmse is not None]
        if not valid_scores:
            continue

        rmses = [s.metrics.rmse for s in valid_scores]
        max_rmse = max(rmses)
        min_rmse = min(rmses)

        for s in valid_scores:
            rmse = s.metrics.rmse
            if rmse is None:  # Should be caught above, but for typing
                continue

            if max_rmse == min_rmse:
                s.normalized_error = 1.0 if rmse > 0 else 0.0
                s.reliability_score = 50.0  # All models perform identically
            else:
                s.normalized_error = (rmse - min_rmse) / (max_rmse - min_rmse)
                s.reliability_score = max(0.0, 100.0 * (1.0 - s.normalized_error))

    return scores
