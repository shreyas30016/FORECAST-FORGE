"""Explanation generation for ensembles."""

from forecast_forge.ensemble.schemas import EnsembleExplanation, EnsembleWeight, ModelForecast


def generate_explanation(
    forecasts: list[ModelForecast],
    weights: list[EnsembleWeight] | None = None,
    variable: str | None = None,
) -> EnsembleExplanation:
    """Generate a structured deterministic text explanation for how the ensemble was formed."""
    dropped_models = [f.model for f in forecasts if not f.is_valid]
    valid_forecasts = [f for f in forecasts if f.is_valid]

    if not valid_forecasts:
        return EnsembleExplanation(
            primary_contributor=None,
            dropped_models=dropped_models,
            reasoning=(
                "All models were dropped due to invalid or missing data. "
                "No ensemble could be formed."
            ),
        )

    reasoning_parts = []
    primary_contributor = None

    # Model name mapping for clean scientific display
    name_map = {
        "ecmwf_ifs025": "ECMWF IFS",
        "gfs_seamless": "NOAA GFS",
        "ecmwf_aifs025": "ECMWF AIFS",
        "ifs": "IFS",
        "gfs": "GFS",
        "aifs": "AIFS",
    }

    if weights:
        # Sort weights descending
        sorted_weights = sorted(weights, key=lambda w: w.weight, reverse=True)
        # Filter for models actually used in this prediction
        valid_model_names = {f.model for f in valid_forecasts}
        valid_weights = [w for w in sorted_weights if w.model in valid_model_names and w.weight > 0]

        if valid_weights:
            total_valid_weight = sum(w.weight for w in valid_weights)
            # Normalize to 100%
            allocations = []
            for w in valid_weights:
                pct = round((w.weight / total_valid_weight) * 100)
                m_label = name_map.get(w.model, w.model.upper())
                allocations.append(f"{pct}% weight to {m_label}")

            primary_contributor = valid_weights[0].model
            var_desc = f" for {variable}" if variable else " for this variable/context"
            weight_text = " and ".join(allocations)
            reasoning_parts.append(
                f"Adaptive ensemble assigns {weight_text} based on the "
                f"evaluated historical skill{var_desc}."
            )
        else:
            reasoning_parts.append(
                "All remaining models received zero weight from the historical baseline."
            )
    else:
        # Baseline fallback
        primary_contributor = "EQUAL_WEIGHT"
        reasoning_parts.append(
            "An equal-weight baseline was used because specific model weights were unavailable."
        )

    # Explicit explanations for unavailable models (especially AIFS)
    for dm in dropped_models:
        dm_label = name_map.get(dm, dm.upper())
        reasoning_parts.append(f"{dm_label} excluded because valid forecast data was unavailable.")

    return EnsembleExplanation(
        primary_contributor=primary_contributor,
        dropped_models=dropped_models,
        reasoning=" ".join(reasoning_parts),
    )
