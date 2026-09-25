"""Script to extract historical data for Mumbai and save to Parquet."""

import asyncio
from datetime import date, timedelta

from forecast_forge.config import get_settings
from forecast_forge.core.models import Location
from forecast_forge.historical.alignment import align_and_calculate_errors
from forecast_forge.historical.extraction import extract_historical_dataset
from forecast_forge.historical.storage import save_historical_dataset
from forecast_forge.logging_config import configure_logging


async def main():
    settings = get_settings()
    configure_logging(settings.log_level)

    mumbai = Location(latitude=19.0760, longitude=72.8777, name="Mumbai")
    end = date.today() - timedelta(
        days=5
    )  # 5 days ago to ensure ERA5 availability (ERA5 usually has a 5-day lag)
    start = end - timedelta(days=7)  # 1 week of data

    print(f"Extracting historical dataset for Mumbai from {start} to {end}")

    models_df, ref_df = await extract_historical_dataset(
        location=mumbai,
        start_date=start,
        end_date=end,
    )

    print(f"Extracted {len(models_df)} model records and {len(ref_df)} reference records.")

    if models_df.empty:
        print("No model records found.")
        return

    aligned = align_and_calculate_errors(models_df, ref_df)

    print(f"Aligned dataset contains {len(aligned)} records.")
    if not aligned.empty:
        path = save_historical_dataset(aligned, "mumbai_historical_sample")
        print(f"Saved to {path}")


if __name__ == "__main__":
    asyncio.run(main())
