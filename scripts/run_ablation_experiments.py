"""Ablation experiments for adaptive ensemble feature sets."""

from pathlib import Path

import pandas as pd

from forecast_forge.ensemble.adaptive import AdaptiveEnsembleModel
from forecast_forge.ensemble.baseline import (
    calculate_equal_weight_ensemble,
    calculate_inverse_error_ensemble,
)
from forecast_forge.ensemble.comparison import split_chronological
from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast


def apply_equal_weight(row, models, var):
    forecasts = []
    for m in models:
        val = row.get(f"{m}_{var}")
        if pd.notna(val):
            forecasts.append(ModelForecast(model=m, value=val, is_valid=True, status="AVAILABLE"))
    return calculate_equal_weight_ensemble(forecasts)


def apply_inverse_error(row, models, var, weights):
    forecasts = []
    for m in models:
        val = row.get(f"{m}_{var}")
        if pd.notna(val):
            forecasts.append(ModelForecast(model=m, value=val, is_valid=True, status="AVAILABLE"))
    return calculate_inverse_error_ensemble(forecasts, weights)


def main():
    file_path = Path("data/raw/mumbai_historical_sample.parquet")
    df = pd.read_parquet(file_path)
    models = ["ecmwf_ifs025", "gfs_seamless"]
    var = "temperature_2m"

    wide_df = df.pivot(
        index="valid_time", columns="model", values=[var, f"ref_{var}", f"err_{var}"]
    ).reset_index()
    wide_df.columns = (
        ["valid_time"]
        + [f"{m}_{var}" for m in df["model"].unique()]
        + [f"{m}_ref" for m in df["model"].unique()]
        + [f"{m}_err" for m in df["model"].unique()]
    )

    first_model = df["model"].unique()[0]
    wide_df[f"ref_{var}"] = wide_df[f"{first_model}_ref"]

    wide_df = wide_df.sort_values("valid_time").reset_index(drop=True)

    # Calculate Trailing Historical Skill (Leakage-free!)
    wide_df = wide_df.set_index("valid_time")
    for m in models:
        err_col = f"{m}_err"
        abs_err = wide_df[err_col].abs()
        # trailing 7 days average MAE, closed='left' means excluding the current row's timestamp
        wide_df[f"{m}_trailing_mae"] = abs_err.rolling(window="7D", closed="left").mean()
        # fill leading NaNs with a large error or the global mean to not drop rows
        wide_df[f"{m}_trailing_mae"] = wide_df[f"{m}_trailing_mae"].fillna(abs_err.mean())
    wide_df = wide_df.reset_index()

    wide_df["equal_weight_temperature_2m"] = wide_df.apply(
        lambda r: apply_equal_weight(r, models, var), axis=1
    )

    weights = [
        EnsembleWeight(model="ecmwf_ifs025", weight=0.73),
        EnsembleWeight(model="gfs_seamless", weight=0.27),
    ]
    wide_df["inverse_error_temperature_2m"] = wide_df.apply(
        lambda r: apply_inverse_error(r, models, var, weights), axis=1
    )

    train_df, val_df, test_df = split_chronological(wide_df, train_frac=0.6, val_frac=0.2)
    test_df_copy = test_df.copy()

    # Run Configs
    configs = {
        "A (Context Only)": "A",
        "B (Models Only)": "B",
        "C (Models + Spread)": "C",
        "D (Models + Spread + Historical)": "D",
    }

    for _name, cfg in configs.items():
        adaptive = AdaptiveEnsembleModel(variable=var, feature_config=cfg)
        adaptive.fit(train_df, models)
        test_df_copy[f"adaptive_{cfg}_{var}"] = adaptive.predict(test_df_copy)

    # Compare
    from forecast_forge.evaluation.metrics import calculate_metrics

    results = []

    def add_res(name, col):
        m = calculate_metrics(test_df_copy[col], test_df_copy[f"ref_{var}"])
        results.append(
            {
                "Approach": name,
                "MAE": m.mae,
                "RMSE": m.rmse,
                "Bias": m.mean_bias,
                "Samples": m.valid_samples,
            }
        )

    add_res("IFS", f"ecmwf_ifs025_{var}")
    add_res("GFS", f"gfs_seamless_{var}")
    add_res("Equal-Weight", f"equal_weight_{var}")
    add_res("Inverse-Error", f"inverse_error_{var}")
    for name, cfg in configs.items():
        add_res(f"Adaptive {name}", f"adaptive_{cfg}_{var}")

    res_df = pd.DataFrame(results)

    print("\n============================================================")
    print("PHASE 4.1 — ABLATION EXPERIMENTS (TEST SET)")
    print("============================================================")
    print(res_df.to_string(index=False))


if __name__ == "__main__":
    main()
