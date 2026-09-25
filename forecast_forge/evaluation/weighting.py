"""Ensemble model weighting based on inverse-error."""

from forecast_forge.evaluation.schemas import ModelScore, WeightResult


def calculate_weights(scores: list[ModelScore], epsilon: float = 1e-6) -> list[WeightResult]:
    """
    Calculate weights for a set of models in the SAME lead time bucket and variable.
    Uses inverse-RMSE.
    Models with is_valid=False receive 0 weight.
    """
    weights = []

    if not scores:
        return weights

    # Validation: ensure all scores belong to the same bucket/variable
    bucket = scores[0].lead_time_bucket
    var = scores[0].variable

    if any(s.lead_time_bucket != bucket or s.variable != var for s in scores):
        raise ValueError("Cannot calculate joint weights across different buckets or variables.")

    raw_weights = []

    for s in scores:
        if not s.is_valid or s.metrics.rmse is None:
            raw_weights.append(0.0)
        else:
            raw_weights.append(1.0 / (s.metrics.rmse + epsilon))

    total_raw = sum(raw_weights)

    for score, raw in zip(scores, raw_weights, strict=False):
        final_weight = raw / total_raw if total_raw > 0 else 0.0

        weights.append(
            WeightResult(
                model=score.model,
                variable=score.variable,
                lead_time_bucket=score.lead_time_bucket,
                weight=final_weight,
                method="inverse_rmse",
            )
        )

    return weights
