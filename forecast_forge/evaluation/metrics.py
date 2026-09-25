"""Statistical metrics engine for model evaluation."""

import numpy as np
import pandas as pd

from forecast_forge.evaluation.schemas import MetricResult


def calculate_metrics(predictions: pd.Series, observations: pd.Series) -> MetricResult:
    """
    Calculate core statistical metrics for a set of predictions and observations.

    Rules enforced:
    - Invalid/null pairs are dropped before calculation.
    - Missing values are NEVER replaced with zero.
    - Sample counts are tracked and returned.
    """
    if len(predictions) != len(observations):
        raise ValueError("Predictions and observations must have the same length.")

    # Create a temporary dataframe to align and drop NaNs simultaneously
    df = pd.DataFrame({"pred": predictions, "obs": observations})

    total_samples = len(df)
    df_valid = df.dropna()
    valid_samples = len(df_valid)
    missing_samples = total_samples - valid_samples

    if valid_samples == 0:
        return MetricResult(
            mae=None, rmse=None, mean_bias=None, valid_samples=0, missing_samples=missing_samples
        )

    preds = df_valid["pred"]
    obs = df_valid["obs"]
    errors = preds - obs

    mae = float(errors.abs().mean())
    rmse = float(np.sqrt((errors**2).mean()))
    mean_bias = float(errors.mean())

    return MetricResult(
        mae=mae,
        rmse=rmse,
        mean_bias=mean_bias,
        valid_samples=valid_samples,
        missing_samples=missing_samples,
    )
