"""Execute the Phase 3 Evaluation Engine on the historical Parquet dataset."""

from pathlib import Path

import pandas as pd

from forecast_forge.config import get_settings
from forecast_forge.evaluation.reports import generate_evaluation_report
from forecast_forge.logging_config import configure_logging


def main():
    settings = get_settings()
    configure_logging(settings.log_level)

    file_path = Path("data/raw/mumbai_historical_sample.parquet")
    if not file_path.exists():
        print(f"Dataset not found at {file_path}. Run Phase 2 extraction first.")
        return

    print(f"Loading dataset from {file_path}...")
    df = pd.read_parquet(file_path)
    print(f"Loaded {len(df)} rows.")

    # Generate the report
    report_text, summary_df = generate_evaluation_report(df)

    print("\n")
    print(report_text)

    out_path = Path("data/processed/mumbai_evaluation_summary.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_parquet(out_path, engine="pyarrow", index=False)
    print(f"\nSaved structured evaluation summary to {out_path}")


if __name__ == "__main__":
    main()
