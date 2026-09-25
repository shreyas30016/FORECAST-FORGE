"""Uncertainty generation logic."""

import numpy as np

from forecast_forge.ensemble.schemas import ModelForecast, UncertaintyResult


def calculate_uncertainty(
    forecasts: list[ModelForecast], expected_total_models: int = 3
) -> UncertaintyResult:
    """Calculate spread and data quality flags."""
    valid_vals = [f.value for f in forecasts if f.is_valid and f.value is not None]
    valid_count = len(valid_vals)

    if valid_count > 1:
        spread = float(np.std(valid_vals, ddof=1))  # Sample standard deviation
    else:
        spread = None

    if valid_count == expected_total_models:
        quality = "HIGH"
    elif valid_count > 0:
        quality = "PARTIAL"
    else:
        quality = "POOR"

    return UncertaintyResult(
        spread=spread,
        valid_model_count=valid_count,
        total_model_count=expected_total_models,
        data_quality_indicator=quality,
    )
