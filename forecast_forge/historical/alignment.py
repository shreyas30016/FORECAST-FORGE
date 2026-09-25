"""Temporal alignment and error calculation."""

import pandas as pd

from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)


def align_and_calculate_errors(models_df: pd.DataFrame, ref_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join model predictions with ERA5 reference and calculate error metrics.
    """
    if models_df.empty or ref_df.empty:
        logger.warning("Cannot align empty dataframes")
        return pd.DataFrame()

    # Join on valid_time
    aligned = pd.merge(
        models_df,
        ref_df.drop(columns=["model", "latitude", "longitude"], errors="ignore"),
        on="valid_time",
        how="inner",
    )

    # Calculate errors
    if not aligned.empty:
        aligned["err_temperature_2m"] = aligned["temperature_2m"] - aligned["ref_temperature_2m"]
        aligned["err_relative_humidity_2m"] = (
            aligned["relative_humidity_2m"] - aligned["ref_relative_humidity_2m"]
        )
        aligned["err_precipitation"] = aligned["precipitation"] - aligned["ref_precipitation"]
        aligned["err_wind_speed_10m"] = aligned["wind_speed_10m"] - aligned["ref_wind_speed_10m"]

    return aligned
