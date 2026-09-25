"""Run real Mumbai evaluation over previous runs with exact scientific auditing."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from forecast_forge.config import get_settings
from forecast_forge.core.models import Location
from forecast_forge.evaluation.lead_time_eval import (
    DEFAULT_LEAD_HOURS,
    DEFAULT_MODELS,
    audit_lead_time_dataset,
    generate_exact_lead_time_evaluation,
)
from forecast_forge.historical.alignment import align_and_calculate_errors
from forecast_forge.historical.extraction import extract_historical_dataset
from forecast_forge.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


async def main():
    settings = get_settings()
    configure_logging(settings.log_level)

    location = Location(latitude=19.0760, longitude=72.8777, name="Mumbai")

    # 30-day verified historical archive window where all models have history
    start_date = date(2024, 6, 1)
    end_date = date(2024, 6, 30)

    print("=" * 105)
    print("PHASE 5E.3 REAL MUMBAI LEAD-TIME EVALUATION AUDIT")
    print(f"Location: Mumbai (19.0760° N, 72.8777° E) | Window: {start_date} to {end_date} (30 days)")
    print("=" * 105)

    logger.info("Extracting Previous Runs dataset for Mumbai (%s to %s)...", start_date, end_date)
    models_df, ref_df = await extract_historical_dataset(
        location=location,
        start_date=start_date,
        end_date=end_date,
        lead_time_days=[1, 2, 3, 4, 5, 6, 7],
    )

    if models_df.empty or ref_df.empty:
        logger.error("Dataset empty.")
        return

    logger.info(
        "Loaded %d model records and %d reference records.", len(models_df), len(ref_df)
    )

    # Standard alignment
    aligned_df = align_and_calculate_errors(models_df, ref_df)
    logger.info("Aligned records count: %d", len(aligned_df))

    # =========================================================================
    # 1. AUDIT & AVAILABILITY MATRIX
    # =========================================================================
    print("\n" + "=" * 105)
    print("1. MODEL AVAILABILITY MATRIX (Variable: temperature_2m)")
    print("=" * 105)

    audit_df = audit_lead_time_dataset(
        aligned_df,
        variables=["temperature_2m"],
        min_samples=5,
        expected_models=DEFAULT_MODELS,
        lead_hours=DEFAULT_LEAD_HOURS,
    )

    # Pivot to display matrix: Rows = Models, Cols = Lead Times
    matrix_rows = []
    for model in DEFAULT_MODELS:
        row = {"Model": model}
        m_audit = audit_df[audit_df["model"] == model]
        for lead in DEFAULT_LEAD_HOURS:
            lead_match = m_audit[m_audit["lead_time_hours"] == lead]
            if not lead_match.empty:
                r = lead_match.iloc[0]
                status = r["status"]
                matched = r["valid_matched_records"]
                total = r["total_records"]
                row[f"{int(lead)}h"] = f"{status} ({matched}/{total})"
            else:
                row[f"{int(lead)}h"] = "UNAVAILABLE (0/0)"
        matrix_rows.append(row)

    matrix_df = pd.DataFrame(matrix_rows)
    print(matrix_df.to_string(index=False))

    # =========================================================================
    # 2. RETROSPECTIVE EVALUATION & METRICS
    # =========================================================================
    print("\n" + "=" * 105)
    print("2. RETROSPECTIVE EVALUATION (Variable: temperature_2m)")
    print("   Mode: RETROSPECTIVE (Aggregated over entire 30-day historical window)")
    print("=" * 105)

    retrospective_df = generate_exact_lead_time_evaluation(
        aligned_df,
        variables=["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
        evaluation_mode="RETROSPECTIVE",
        min_samples=5,
        expected_models=DEFAULT_MODELS,
    )

    sample_retro = retrospective_df[retrospective_df["variable"] == "temperature_2m"].sort_values(
        by=["lead_time_hours", "model"]
    )

    header = (
        f"{'Model':<15} {'Lead':<7} {'MAE':<7} {'RMSE':<7} {'Bias':<7} "
        f"{'Samples':<9} {'Weight':<8} {'Status':<18} {'Mode'}"
    )
    print(header)
    print("-" * 105)

    for _, row in sample_retro.iterrows():
        mae_str = f"{row['mae']:.2f}" if pd.notna(row["mae"]) else "None"
        rmse_str = f"{row['rmse']:.2f}" if pd.notna(row["rmse"]) else "None"
        bias_str = f"{row['bias']:.2f}" if pd.notna(row["bias"]) else "None"
        weight_str = f"{row['weight']:.4f}"
        print(
            f"{row['model']:<15} {int(row['lead_time_hours']):<4}h  {mae_str:<7} {rmse_str:<7} "
            f"{bias_str:<7} {row['valid_samples']:<9} {weight_str:<8} {row['status']:<18} {row['evaluation_mode']}"
        )

    # =========================================================================
    # 3. CAUSAL OPERATIONAL EVALUATION & LEAKAGE CHECK
    # =========================================================================
    print("\n" + "=" * 105)
    print("3. CAUSAL OPERATIONAL EVALUATION & WEIGHTS")
    print("   Mode: CAUSAL_OPERATIONAL (Strict cutoff at T - 24h, zero future data leakage)")
    print("=" * 105)

    target_time = datetime(2024, 6, 25, 0, 0, tzinfo=UTC)
    causal_cutoff = datetime(2024, 6, 20, 0, 0, tzinfo=UTC)  # 5 days strictly before forecast

    causal_df = generate_exact_lead_time_evaluation(
        aligned_df,
        variables=["temperature_2m"],
        evaluation_mode="CAUSAL_OPERATIONAL",
        causal_cutoff=causal_cutoff,
        target_forecast_time=target_time,
        min_samples=5,
        expected_models=DEFAULT_MODELS,
    )

    sample_causal = causal_df[causal_df["variable"] == "temperature_2m"].sort_values(
        by=["lead_time_hours", "model"]
    )

    print(header)
    print("-" * 105)
    for _, row in sample_causal.iterrows():
        mae_str = f"{row['mae']:.2f}" if pd.notna(row["mae"]) else "None"
        rmse_str = f"{row['rmse']:.2f}" if pd.notna(row["rmse"]) else "None"
        bias_str = f"{row['bias']:.2f}" if pd.notna(row["bias"]) else "None"
        weight_str = f"{row['weight']:.4f}"
        print(
            f"{row['model']:<15} {int(row['lead_time_hours']):<4}h  {mae_str:<7} {rmse_str:<7} "
            f"{bias_str:<7} {row['valid_samples']:<9} {weight_str:<8} {row['status']:<18} {row['evaluation_mode']}"
        )

    # =========================================================================
    # 4. LEAD-TIME WEIGHT MATRIX
    # =========================================================================
    print("\n" + "=" * 105)
    print("4. LEAD-TIME WEIGHT MATRIX (Independent inverse-RMSE weights)")
    print("=" * 105)

    weight_matrix_rows = []
    for model in DEFAULT_MODELS:
        w_row = {"Model": model}
        m_retro = sample_retro[sample_retro["model"] == model]
        for lead in DEFAULT_LEAD_HOURS:
            lead_match = m_retro[m_retro["lead_time_hours"] == lead]
            if not lead_match.empty:
                w_row[f"{int(lead)}h"] = f"{lead_match.iloc[0]['weight']:.4f}"
            else:
                w_row[f"{int(lead)}h"] = "0.0000"
        weight_matrix_rows.append(w_row)

    weight_matrix_df = pd.DataFrame(weight_matrix_rows)
    print(weight_matrix_df.to_string(index=False))

    # Save retrospective dataset summary for API serving
    out_path = Path("data/processed/mumbai_lead_time_evaluation_summary.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    retrospective_df.to_parquet(out_path, engine="pyarrow", index=False)
    logger.info("Saved lead-time evaluation summary to %s", out_path)


if __name__ == "__main__":
    asyncio.run(main())
