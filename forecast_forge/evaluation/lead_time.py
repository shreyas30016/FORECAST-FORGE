"""Lead-time calculation and bucketization."""

from datetime import timedelta

import pandas as pd


def calculate_lead_time_hours(
    df: pd.DataFrame, init_col: str = "initialization_time", valid_col: str = "valid_time"
) -> pd.Series:
    """Calculate lead time in hours. Validates that valid_time >= init_time."""
    if df.empty or init_col not in df.columns or valid_col not in df.columns:
        return pd.Series(dtype=float)

    diff = df[valid_col] - df[init_col]

    # Leakage check: valid_time must not be before initialization_time
    if (diff < timedelta(0)).any():
        raise ValueError("Temporal leakage detected: valid_time is before initialization_time.")

    return diff.dt.total_seconds() / 3600.0


def assign_lead_time_bucket(
    lead_time_hours: pd.Series, buckets: list[tuple[float, float, str]] | None = None
) -> pd.Series:
    """
    Assign continuous lead times to categorical buckets.
    Bucket format: (min_inclusive, max_exclusive, label)
    """
    if buckets is None:
        buckets = [
            (0, 6, "0-6h"),
            (6, 12, "6-12h"),
            (12, 24, "12-24h"),
            (24, 48, "24-48h"),
            (48, 72, "48-72h"),
            (72, 120, "72-120h"),
            (120, 168, "120-168h"),
            (168, float("inf"), "168h+"),
        ]

    result = pd.Series(index=lead_time_hours.index, dtype=str)

    for min_h, max_h, label in buckets:
        mask = (lead_time_hours >= min_h) & (lead_time_hours < max_h)
        result.loc[mask] = label

    # Fill remaining unassigned (e.g., negative/NaN) with "Unknown"
    result = result.fillna("Unknown")
    return result
