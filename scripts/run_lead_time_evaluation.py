"""Run real lead-time evaluation over previous runs with exact scientific auditing."""

import argparse
import asyncio
from datetime import date
from pathlib import Path

import pandas as pd

from forecast_forge.config import get_settings
from forecast_forge.core.models import Location
from forecast_forge.evaluation.lead_time_eval import (
    DEFAULT_MODELS,
    generate_exact_lead_time_evaluation,
)
from forecast_forge.historical.alignment import align_and_calculate_errors
from forecast_forge.historical.extraction import extract_historical_dataset
from forecast_forge.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

KNOWN_LOCATIONS = {
    "Mumbai": Location(latitude=19.0760, longitude=72.8777, name="Mumbai"),
    "Delhi": Location(latitude=28.6139, longitude=77.2090, name="Delhi"),
    "Chennai": Location(latitude=13.0827, longitude=80.2707, name="Chennai"),
    "Jaipur": Location(latitude=26.9124, longitude=75.7873, name="Jaipur"),
    "Guwahati": Location(latitude=26.1445, longitude=91.7362, name="Guwahati"),
}


async def main():
    parser = argparse.ArgumentParser(description="Run lead-time evaluation")
    parser.add_argument(
        "--locations",
        nargs="+",
        default=["Mumbai"],
        choices=list(KNOWN_LOCATIONS.keys()) + ["ALL"],
        help="Locations to evaluate (e.g. Mumbai Delhi or ALL)"
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    if "ALL" in args.locations:
        locs_to_run = list(KNOWN_LOCATIONS.values())
    else:
        locs_to_run = [KNOWN_LOCATIONS[name] for name in args.locations]

    # 30-day verified historical archive window where all models have history
    start_date = date(2024, 6, 1)
    end_date = date(2024, 6, 30)

    print("=" * 105)
    print("PHASE 6.8 MULTI-LOCATION VALIDATION EXPERIMENT")
    print(f"Window: {start_date} to {end_date} (30 days)")
    print("Locations:", [loc.name for loc in locs_to_run])
    print("=" * 105)

    all_results = []

    for location in locs_to_run:
        print(f"\nProcessing {location.name} ({location.latitude}, {location.longitude})...")

        models_df, ref_df = await extract_historical_dataset(
            location=location,
            start_date=start_date,
            end_date=end_date,
            lead_time_days=[1, 2, 3, 4, 5, 6, 7],
        )

        if models_df.empty or ref_df.empty:
            logger.error("Dataset empty for %s.", location.name)
            continue

        aligned_df = align_and_calculate_errors(models_df, ref_df)
        if aligned_df.empty:
            logger.error("Aligned dataset empty for %s.", location.name)
            continue

        retrospective_df = generate_exact_lead_time_evaluation(
            aligned_df,
            variables=["temperature_2m"],
            evaluation_mode="RETROSPECTIVE",
            min_samples=5,
            expected_models=DEFAULT_MODELS,
        )

        # Add location metadata
        retrospective_df["location"] = location.name
        retrospective_df["latitude"] = location.latitude
        retrospective_df["longitude"] = location.longitude
        retrospective_df["evaluation_start"] = start_date
        retrospective_df["evaluation_end"] = end_date
        retrospective_df["reference_source"] = "ERA5"

        # generate_exact_lead_time_evaluation already returns sample_count and valid_samples

        all_results.append(retrospective_df)

        # Print a small summary for the city
        sample_retro = retrospective_df.sort_values(by=["lead_time_hours", "model"])
        header = f"{'Model':<15} {'Lead':<7} {'MAE':<7} {'RMSE':<7} {'Bias':<7} {'Samples':<9} {'Weight':<8} {'Status':<18}"
        print(header)
        print("-" * 95)
        for _, row in sample_retro.iterrows():
            if row["lead_time_hours"] not in [24, 72, 168]:
                continue # Only print a few leads to save space
            mae_str = f"{row['mae']:.2f}" if pd.notna(row['mae']) else "None"
            rmse_str = f"{row['rmse']:.2f}" if pd.notna(row['rmse']) else "None"
            bias_str = f"{row['bias']:.2f}" if pd.notna(row['bias']) else "None"
            weight_str = f"{float(row['weight']):.4f}" if pd.notna(row['weight']) else "0.0000"
            print(f"{str(row['model']):<15} {int(row['lead_time_hours']):<4}h  {mae_str:<7} {rmse_str:<7} {bias_str:<7} {int(row.get('sample_count', 0)):<9} {weight_str:<8} {str(row['status']):<18}")

    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        # Reorder columns explicitly to match Phase 6.8 requirements
        cols = [
            "location", "latitude", "longitude", "variable", "lead_time_hours",
            "model", "sample_count", "mae", "rmse", "bias", "weight", "status",
            "evaluation_start", "evaluation_end", "reference_source", "evaluation_mode"
        ]
        # Only select columns that exist to prevent errors if evaluation_mode is missing etc.
        cols = [c for c in cols if c in final_df.columns]
        final_df = final_df[cols]

        out_path = Path("data/processed/multi_location_validation.parquet")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_parquet(out_path, engine="pyarrow", index=False)
        print(f"\nSaved combined multi-location evaluation to {out_path}")

        # Also print a summary comparing weights at 24h
        print("\n" + "=" * 105)
        print("MULTI-LOCATION WEIGHT COMPARISON (24h Lead Time, temperature_2m)")
        print("=" * 105)
        df_24h = final_df[(final_df["lead_time_hours"] == 24) & (final_df["variable"] == "temperature_2m")]
        pivot = df_24h.pivot(index="location", columns="model", values="weight").fillna(0)
        print(pivot.to_string())

        # Comparison at 72h
        print("\n" + "=" * 105)
        print("MULTI-LOCATION WEIGHT COMPARISON (72h Lead Time, temperature_2m)")
        print("=" * 105)
        df_72h = final_df[(final_df["lead_time_hours"] == 72) & (final_df["variable"] == "temperature_2m")]
        pivot_72h = df_72h.pivot(index="location", columns="model", values="weight").fillna(0)
        print(pivot_72h.to_string())


if __name__ == "__main__":
    asyncio.run(main())
