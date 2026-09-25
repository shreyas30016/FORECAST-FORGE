"""Operational regime assignment."""

import pandas as pd

from forecast_forge.evaluation.regimes.clustering import RegimeDiscoveryPipeline
from forecast_forge.evaluation.regimes.metadata import RegimeAssignment
from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)

FORECAST_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "cloud_cover",
]


class RegimeAssigner:
    """Assigns weather regimes to operational forecast states without refitting."""

    def __init__(self, pipeline: RegimeDiscoveryPipeline):
        if not pipeline.is_fitted:
            raise ValueError("RegimeAssigner requires a fitted RegimeDiscoveryPipeline.")
        self.pipeline = pipeline

    def assign_forecast_state(self, forecast_dict: dict[str, float | None]) -> RegimeAssignment:
        """Assign a single operational forecast state dict to a regime."""
        missing = []
        features = []

        for feat in FORECAST_FEATURES:
            val = forecast_dict.get(feat)
            if val is None:
                missing.append(feat)
            else:
                features.append(val)

        if missing:
            return RegimeAssignment(
                regime_id=None, is_valid=False, status="UNAVAILABLE", missing_features=missing
            )

        import numpy as np

        X = np.array(features).reshape(1, -1)
        X_scaled = self.pipeline.scaler.transform(X)
        pred = self.pipeline.model.predict(X_scaled)[0]

        return RegimeAssignment(
            regime_id=int(pred), is_valid=True, status="AVAILABLE", missing_features=[]
        )

    def assign_forecast_df(self, forecast_df: pd.DataFrame) -> pd.DataFrame:
        """Assign regimes to a dataframe of forecast states."""
        res_df = forecast_df.copy()
        res_df["regime_id"] = None

        valid_mask = res_df[FORECAST_FEATURES].notna().all(axis=1)
        if valid_mask.any():
            X = res_df.loc[valid_mask, FORECAST_FEATURES].values
            X_scaled = self.pipeline.scaler.transform(X)
            preds = self.pipeline.model.predict(X_scaled)
            res_df.loc[valid_mask, "regime_id"] = preds

        return res_df
