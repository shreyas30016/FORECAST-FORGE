"""Core orchestration engine for generating ensemble forecasts."""

from datetime import datetime

import pandas as pd

from forecast_forge.ensemble.adaptive import AdaptiveEnsembleModel
from forecast_forge.ensemble.baseline import (
    calculate_equal_weight_ensemble,
    calculate_inverse_error_ensemble,
)
from forecast_forge.ensemble.explanations import generate_explanation
from forecast_forge.ensemble.schemas import EnsembleResult, EnsembleWeight, ModelForecast
from forecast_forge.ensemble.uncertainty import calculate_uncertainty


def generate_ensemble_forecast(
    location_name: str,
    variable: str,
    valid_time: datetime,
    forecasts: list[ModelForecast],
    historical_weights: list[EnsembleWeight] | None = None,
    adaptive_model: AdaptiveEnsembleModel | None = None,
    expected_total_models: int = 3,
) -> EnsembleResult:
    """
    Generate a complete ensemble forecast including baselines and adaptive ML (if available).
    """
    # 1. Baselines
    equal_weight = calculate_equal_weight_ensemble(forecasts)

    inverse_error = None
    if historical_weights:
        inverse_error = calculate_inverse_error_ensemble(forecasts, historical_weights)

    # 2. Adaptive
    adaptive_val = None
    adaptive_weights = None

    if adaptive_model and adaptive_model.is_fitted:
        # We must construct a one-row DataFrame to feed the predictor
        row_dict = {"valid_time": valid_time}
        for f in forecasts:
            # We pass the raw value if valid, else NaN (handled by adaptive model)
            row_dict[f"{f.model}_{variable}"] = (
                f.value if (f.is_valid and f.value is not None) else None
            )

        df_input = pd.DataFrame([row_dict])
        preds = adaptive_model.predict(df_input)
        adaptive_val = float(preds[0])
        adaptive_weights = adaptive_model.get_dynamic_weights()

    # 3. Meta (Uncertainty & Explanation)
    uncertainty = calculate_uncertainty(forecasts, expected_total_models)

    # We explain based on the adaptive weights if available, else historical, else none
    weights_for_explanation = adaptive_weights if adaptive_weights else historical_weights
    explanation = generate_explanation(forecasts, weights_for_explanation, variable=variable)

    return EnsembleResult(
        location_name=location_name,
        variable=variable,
        valid_time=valid_time,
        model_forecasts=forecasts,
        equal_weight_forecast=equal_weight,
        inverse_error_forecast=inverse_error,
        adaptive_forecast=adaptive_val,
        adaptive_weights=adaptive_weights,
        uncertainty=uncertainty,
        explanation=explanation,
    )
