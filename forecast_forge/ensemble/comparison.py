"""Comparison and evaluation of ensemble against individual models."""

import pandas as pd

from forecast_forge.evaluation.metrics import calculate_metrics


def compare_ensembles_historically(
    df: pd.DataFrame,
    variable: str,
    models: list[str],
    equal_weight_col: str,
    inverse_error_col: str | None = None,
    adaptive_col: str | None = None,
) -> pd.DataFrame:
    """
    Compare individual models against ensembles for a specific variable.
    Returns a DataFrame with columns:
    Approach, MAE, RMSE, Bias, Samples.
    """
    results = []

    target_col = f"ref_{variable}"
    if target_col not in df.columns:
        return pd.DataFrame()

    def add_result(name: str, pred_col: str):
        if pred_col in df.columns:
            m = calculate_metrics(df[pred_col], df[target_col])
            results.append(
                {
                    "Approach": name,
                    "MAE": m.mae,
                    "RMSE": m.rmse,
                    "Bias": m.mean_bias,
                    "Samples": m.valid_samples,
                }
            )

    # 1. Individual models
    for model in models:
        add_result(model.upper(), f"{model}_{variable}")

    # 2. Ensembles
    add_result("EQUAL-WEIGHT", equal_weight_col)
    if inverse_error_col:
        add_result("INVERSE-ERROR", inverse_error_col)
    if adaptive_col:
        add_result("ADAPTIVE", adaptive_col)

    return pd.DataFrame(results)


def split_chronological(
    df: pd.DataFrame, train_frac: float = 0.6, val_frac: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Chronologically split a dataframe into Train, Validation, and Test."""
    if df.empty or "valid_time" not in df.columns:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Ensure sorted chronologically
    df_sorted = df.sort_values("valid_time").copy()
    n = len(df_sorted)

    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train_df = df_sorted.iloc[:train_end]
    val_df = df_sorted.iloc[train_end:val_end]
    test_df = df_sorted.iloc[val_end:]

    return train_df, val_df, test_df
