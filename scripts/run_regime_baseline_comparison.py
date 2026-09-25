"""Phase 5F: Baseline vs Regime-Conditioned Weights on untouched Test split."""

import asyncio
import logging
from datetime import date

import numpy as np
import pandas as pd

from forecast_forge.core.models import Location
from forecast_forge.evaluation.lead_time_eval import generate_exact_lead_time_evaluation
from forecast_forge.evaluation.regimes import (
    RegimeDiscoveryPipeline,
    generate_regime_conditioned_skill,
)
from forecast_forge.historical.extraction import extract_historical_dataset

logging.getLogger("httpx").setLevel(logging.WARNING)

async def main():
    print("Fetching historical data for evaluation...")
    mumbai = Location(latitude=19.0760, longitude=72.8777, name="Mumbai")
    models_df, ref_df = await extract_historical_dataset(
        location=mumbai,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 7, 31)
    )

    if models_df.empty or ref_df.empty:
        print("Data extraction failed.")
        return

    print("Loading persisted K=3 regime pipeline...")
    pipeline = RegimeDiscoveryPipeline.load(".model_cache/regimes/mumbai_k3.joblib")

    # We join models and refs on valid_time and lead_time_hours
    ref_df["valid_date"] = ref_df["valid_time"].dt.date
    models_df["valid_date"] = models_df["valid_time"].dt.date

    # 1. Transform reference data to get true regime_id
    ref_assigned = pipeline.transform(ref_df)

    # Merge forecast and reference
    if "model" in ref_assigned.columns:
        ref_assigned = ref_assigned.drop(columns=["model"])
    merged = pd.merge(models_df, ref_assigned, on=["valid_time", "latitude", "longitude"], how="inner")

    # Train + Val Split -> Knowledge base
    kb_df = merged[merged["valid_date_x"] <= date(2024, 7, 12)].copy()

    # Test Split -> Untouched evaluation
    test_df = merged[merged["valid_date_x"] > date(2024, 7, 12)].copy()

    print(f"\nKnowledge Base (Train+Val) samples: {len(kb_df)}")
    print(f"Test Set (Out-of-sample) samples: {len(test_df)}")

    print("\nCalculating BASELINE (5E.4 Spatial x Lead-Time) Weights on KB...")
    # Baseline weights (ignoring regime_id)
    baseline_skill = generate_exact_lead_time_evaluation(
        df=kb_df,
        variables=["temperature_2m"],
        evaluation_mode="RETROSPECTIVE",
        lead_hours=[24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]
    )

    print("Calculating REGIME-CONDITIONED Weights on KB...")
    regime_skill = generate_regime_conditioned_skill(
        df=kb_df,
        variables=["temperature_2m"],
        evaluation_mode="RETROSPECTIVE",
        lead_hours=[24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]
    )

    # Save regime skill to parquet for API
    import os
    os.makedirs("data/processed", exist_ok=True)
    regime_skill.to_parquet("data/processed/mumbai_regime_weights.parquet")
    print("Saved regime weights to data/processed/mumbai_regime_weights.parquet")

    print("\n--- OUT-OF-SAMPLE COMPARISON ON TEST SPLIT ---")

    # We will score 24h lead time for temperature_2m on the test set
    lead = 24.0
    var = "temperature_2m"
    ref_var = f"ref_{var}"

    test_24 = test_df[(test_df["lead_time_hours"] == lead)].copy()

    # For each true timestamp in the test set, we construct an ensemble using both weight sets
    results = []

    for valid_time, group in test_24.groupby("valid_time"):
        if ref_var not in group.columns:
            continue
        true_val = group[ref_var].iloc[0]
        if pd.isna(true_val):
            continue

        regime_id = group["regime_id"].iloc[0]
        if pd.isna(regime_id):
            continue

        # Get models and values
        model_vals = {row["model"]: row[var] for _, row in group.iterrows() if pd.notna(row[var])}

        # Baseline Ensemble
        base_w = baseline_skill[(baseline_skill["lead_time_hours"] == lead) & (baseline_skill["variable"] == var)]
        base_pred = 0.0
        b_sum = 0.0
        for m, v in model_vals.items():
            w = base_w[base_w["model"] == m]["weight"].values
            if len(w) > 0:
                base_pred += v * w[0]
                b_sum += w[0]
        base_pred = base_pred / b_sum if b_sum > 0 else np.nan

        # Regime Ensemble
        reg_w = regime_skill[(regime_skill["lead_time_hours"] == lead) & (regime_skill["variable"] == var) & (regime_skill["regime_id"] == regime_id)]
        reg_pred = 0.0
        r_sum = 0.0
        for m, v in model_vals.items():
            w = reg_w[reg_w["model"] == m]["weight"].values
            if len(w) > 0:
                reg_pred += v * w[0]
                r_sum += w[0]
        reg_pred = reg_pred / r_sum if r_sum > 0 else np.nan

        if not pd.isna(base_pred) and not pd.isna(reg_pred):
            results.append({
                "valid_time": valid_time,
                "regime_id": regime_id,
                "true": true_val,
                "base_pred": base_pred,
                "reg_pred": reg_pred,
                "base_error": base_pred - true_val,
                "reg_error": reg_pred - true_val
            })

    res_df = pd.DataFrame(results)

    print(f"\nEvaluated on {len(res_df)} Test timestamps.")

    base_mae = res_df["base_error"].abs().mean()
    base_rmse = np.sqrt((res_df["base_error"]**2).mean())
    base_bias = res_df["base_error"].mean()

    reg_mae = res_df["reg_error"].abs().mean()
    reg_rmse = np.sqrt((res_df["reg_error"]**2).mean())
    reg_bias = res_df["reg_error"].mean()

    print("\nAggregate Test Performance (24h Lead, Temp):")
    print(f"BASELINE:   MAE: {base_mae:.3f} | RMSE: {base_rmse:.3f} | Bias: {base_bias:.3f}")
    print(f"REGIME-AWARE: MAE: {reg_mae:.3f} | RMSE: {reg_rmse:.3f} | Bias: {reg_bias:.3f}")
    print(f"Difference: RMSE improved by {base_rmse - reg_rmse:.3f}")

    print("\nPerformance by True Regime:")
    for rid, rg in res_df.groupby("regime_id"):
        b_rmse = np.sqrt((rg["base_error"]**2).mean())
        r_rmse = np.sqrt((rg["reg_error"]**2).mean())
        print(f"Regime {rid} ({len(rg)} samples): Base RMSE: {b_rmse:.3f} | Regime RMSE: {r_rmse:.3f} -> Diff: {b_rmse - r_rmse:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
