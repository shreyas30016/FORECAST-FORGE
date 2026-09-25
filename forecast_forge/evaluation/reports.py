"""Structured evaluation reports generator."""

import pandas as pd

from forecast_forge.evaluation.lead_time import assign_lead_time_bucket, calculate_lead_time_hours
from forecast_forge.evaluation.scoring import generate_model_scores, normalize_scores
from forecast_forge.evaluation.weighting import calculate_weights


def generate_evaluation_report(
    df: pd.DataFrame, variables: list[str] | None = None
) -> tuple[str, pd.DataFrame]:
    """
    Generate a full statistical evaluation report from an aligned historical dataset.
    Returns:
        tuple[str, pd.DataFrame]: The formatted text report and the summary DataFrame.
    """
    if df.empty:
        return "Empty dataset. No evaluation generated.", pd.DataFrame()

    if variables is None:
        variables = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"]

    # 1. Prepare lead time
    if "lead_time_hours" not in df.columns:
        df["lead_time_hours"] = calculate_lead_time_hours(df)

    df["lead_time_bucket"] = assign_lead_time_bucket(df["lead_time_hours"])

    models = df["model"].unique().tolist()

    all_scores = []

    # 2. Score models
    for var in variables:
        ref_col = f"ref_{var}"
        if var not in df.columns or ref_col not in df.columns:
            continue

        for model in models:
            model_scores = generate_model_scores(df, model, var)
            all_scores.extend(model_scores)

    # 3. Normalize scores
    normalized_scores = normalize_scores(all_scores)

    # 4. Group by bucket/variable and calculate weights
    bucket_var_map = {}
    for s in normalized_scores:
        key = (s.lead_time_bucket, s.variable)
        bucket_var_map.setdefault(key, []).append(s)

    final_weights = {}
    for _key, scores in bucket_var_map.items():
        weights = calculate_weights(scores)
        for w in weights:
            final_weights[(w.lead_time_bucket, w.variable, w.model)] = w

    # 5. Build Report
    lines = []
    lines.append("=" * 60)
    lines.append("FORECAST FORGE AI — MODEL EVALUATION")
    lines.append("=" * 60)
    lines.append("")

    summary_data = []

    for var in variables:
        var_scores = [s for s in normalized_scores if s.variable == var]
        if not var_scores:
            continue

        lines.append(f"Variable: {var}")
        lines.append("")

        # Sort buckets (naive sort is fine for now)
        buckets = sorted(list(set(s.lead_time_bucket for s in var_scores)))

        for bucket in buckets:
            lines.append(f"Lead Time: {bucket}")
            lines.append("")

            header = (
                f"{'Model':<15} {'MAE':<8} {'RMSE':<8} {'Bias':<8} "
                f"{'Samples':<8} {'Score':<8} {'Weight':<8}"
            )
            lines.append(header)

            bucket_scores = [s for s in var_scores if s.lead_time_bucket == bucket]

            for score in bucket_scores:
                weight_obj = final_weights.get((bucket, var, score.model))
                weight_val = weight_obj.weight if weight_obj else 0.0

                mae_str = f"{score.metrics.mae:.2f}" if score.metrics.mae is not None else "N/A"
                rmse_str = f"{score.metrics.rmse:.2f}" if score.metrics.rmse is not None else "N/A"
                bias_str = (
                    f"{score.metrics.mean_bias:.2f}"
                    if score.metrics.mean_bias is not None
                    else "N/A"
                )
                rel_str = (
                    f"{score.reliability_score:.1f}"
                    if score.reliability_score is not None
                    else "N/A"
                )
                weight_str = f"{weight_val:.2f}"

                lines.append(
                    f"{score.model:<15} {mae_str:<8} {rmse_str:<8} {bias_str:<8} "
                    f"{score.metrics.valid_samples:<8} {rel_str:<8} {weight_str:<8}"
                )

                summary_data.append(
                    {
                        "variable": var,
                        "lead_time_bucket": bucket,
                        "model": score.model,
                        "mae": score.metrics.mae,
                        "rmse": score.metrics.rmse,
                        "bias": score.metrics.mean_bias,
                        "valid_samples": score.metrics.valid_samples,
                        "reliability_score": score.reliability_score,
                        "weight": weight_val,
                    }
                )

            lines.append("")

        lines.append("-" * 60)

    return "\n".join(lines), pd.DataFrame(summary_data)
