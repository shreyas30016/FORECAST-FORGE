"""Dataset persistence via Parquet."""

from pathlib import Path

import pandas as pd

from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)


def save_historical_dataset(df: pd.DataFrame, dataset_name: str, base_dir: str = "data/raw") -> str:
    """Save the aligned dataframe to parquet."""
    if df.empty:
        logger.warning("Empty dataframe, not saving")
        return ""

    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)

    file_path = path / f"{dataset_name}.parquet"

    # PyArrow engine handles pandas types well
    df.to_parquet(file_path, engine="pyarrow", index=False)

    logger.info("Saved dataset to %s (%d rows)", file_path, len(df))
    return str(file_path)
