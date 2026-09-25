"""Compare baseline and adaptive ensembles over historical data."""

from pathlib import Path

import pandas as pd

from forecast_forge.config import get_settings
from forecast_forge.ensemble.adaptive import AdaptiveEnsembleModel
from forecast_forge.ensemble.baseline import (
    calculate_equal_weight_ensemble,
    calculate_inverse_error_ensemble,
)
from forecast_forge.ensemble.comparison import compare_ensembles_historically, split_chronological
from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast
from forecast_forge.logging_config import configure_logging


def apply_equal_weight(row, models, var):
    forecasts = []
    for m in models:
        val = row.get(f"{m}_{var}")
        if pd.notna(val):
            forecasts.append(ModelForecast(model=m, value=val, is_valid=True))
    return calculate_equal_weight_ensemble(forecasts)


def apply_inverse_error(row, models, var, weights):
    forecasts = []
    for m in models:
        val = row.get(f"{m}_{var}")
        if pd.notna(val):
            forecasts.append(ModelForecast(model=m, value=val, is_valid=True))
    return calculate_inverse_error_ensemble(forecasts, weights)


def main():
    settings = get_settings()
    configure_logging(settings.log_level)

    file_path = Path("data/raw/mumbai_historical_sample.parquet")
    if not file_path.exists():
        print("Historical dataset not found.")
        return

    df = pd.read_parquet(file_path)
    models = ["ecmwf_ifs025", "gfs_seamless"]
    var = "temperature_2m"

    # Restructure dataframe so models have their own columns
    # (In Phase 2, we stored it as long-format, let's pivot to wide format for the ensemble script)
    # The dataframe has 'model', 'valid_time', 'temperature_2m'

    wide_df = df.pivot(
        index="valid_time", columns="model", values=[var, f"ref_{var}"]
    ).reset_index()
    # Flatten multi-index columns
    wide_df.columns = (
        ["valid_time"]
        + [f"{m}_{var}" for m in df["model"].unique()]
        + [f"{m}_ref" for m in df["model"].unique()]
    )

    # The reference truth is identical across models for a given valid_time, so just take the first one
    first_model = df["model"].unique()[0]
    wide_df[f"ref_{var}"] = wide_df[f"{first_model}_ref"]

    # Generate Equal Weight
    wide_df["equal_weight_temperature_2m"] = wide_df.apply(
        lambda r: apply_equal_weight(r, models, var), axis=1
    )

    # Dummy inverse weights based on Phase 3 evaluation output
    weights = [
        EnsembleWeight(model="ecmwf_ifs025", weight=0.73),
        EnsembleWeight(model="gfs_seamless", weight=0.27),
    ]
    wide_df["inverse_error_temperature_2m"] = wide_df.apply(
        lambda r: apply_inverse_error(r, models, var, weights), axis=1
    )

    # Chronological Split
    train_df, val_df, test_df = split_chronological(wide_df, train_frac=0.6, val_frac=0.2)

    # Train Adaptive Model
    print(f"Training Adaptive Model on {len(train_df)} rows...")
    adaptive = AdaptiveEnsembleModel(variable=var)
    adaptive.fit(train_df, models)

    # Predict on Test
    test_df_copy = test_df.copy()
    print(f"Evaluating on {len(test_df_copy)} out-of-sample rows...")
    test_df_copy["adaptive_temperature_2m"] = adaptive.predict(test_df_copy)

    # Compare
    comparison = compare_ensembles_historically(
        df=test_df_copy,
        variable=var,
        models=models,
        equal_weight_col="equal_weight_temperature_2m",
        inverse_error_col="inverse_error_temperature_2m",
        adaptive_col="adaptive_temperature_2m",
    )

    print("\n============================================================")
    print("FORECAST FORGE AI — ENSEMBLE COMPARISON (TEST SET)")
    print("============================================================")
    print(comparison.to_string(index=False))

    adaptive_weights = adaptive.get_dynamic_weights()
    print("\nAdaptive ML Learned Weights (for this period):")
    for w in adaptive_weights:
        print(f"  {w.model}: {w.weight:.3f}")


if __name__ == "__main__":
    main()
