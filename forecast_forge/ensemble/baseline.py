"""Baseline ensemble strategies: Equal-Weight and Inverse-Error."""

import numpy as np

from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast


def calculate_equal_weight_ensemble(forecasts: list[ModelForecast]) -> float | None:
    """Calculate simple average of valid model forecasts."""
    valid_vals = [f.value for f in forecasts if f.is_valid and f.value is not None]
    if not valid_vals:
        return None
    return float(np.mean(valid_vals))


def calculate_inverse_error_ensemble(
    forecasts: list[ModelForecast], weights: list[EnsembleWeight]
) -> float | None:
    """Calculate weighted average using historical inverse-error weights."""
    valid_forecasts = {f.model: f.value for f in forecasts if f.is_valid and f.value is not None}
    if not valid_forecasts:
        return None

    # Re-normalize weights to only include available models
    applicable_weights = {}
    total_weight = 0.0

    for w in weights:
        if w.model in valid_forecasts:
            applicable_weights[w.model] = w.weight
            total_weight += w.weight

    if total_weight <= 0:
        # Fallback to equal weight if no historical weights exist for available models
        return calculate_equal_weight_ensemble(forecasts)

    ensemble_val = 0.0
    for model, val in valid_forecasts.items():
        if model in applicable_weights:
            normalized_weight = applicable_weights[model] / total_weight
            ensemble_val += val * normalized_weight

    return float(ensemble_val)
