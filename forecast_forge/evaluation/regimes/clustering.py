"""Unsupervised clustering for Weather Regime Discovery."""

import os

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from forecast_forge.evaluation.regimes.metadata import RegimeDefinition, RegimeFeatureSummary
from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)

# Features expected from ERA5 reference dataset
REFERENCE_FEATURES = [
    "ref_temperature_2m",
    "ref_relative_humidity_2m",
    "ref_precipitation",
    "ref_wind_speed_10m",
    "ref_cloud_cover",
]


class RegimeDiscoveryPipeline:
    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = KMeans(
            n_clusters=self.n_clusters, random_state=self.random_state, n_init="auto"
        )
        self.is_fitted = False
        self.regimes: list[RegimeDefinition] = []

    def fit(self, ref_df: pd.DataFrame, training_period: str = "Unknown") -> list[RegimeDefinition]:
        """Fit the scaler and KMeans model strictly on the historical training split."""
        if ref_df.empty:
            raise ValueError("Reference DataFrame is empty.")

        # Extract features and drop rows with missing values
        feature_df = ref_df[REFERENCE_FEATURES].dropna()
        if feature_df.empty:
            raise ValueError("No valid rows remaining after dropping NAs for clustering.")

        X = feature_df.values

        # Fit scaler and transform
        X_scaled = self.scaler.fit_transform(X)

        # Fit KMeans
        self.model.fit(X_scaled)
        self.is_fitted = True

        # Calculate cluster populations and centroids (in original physical units)
        centroids_scaled = self.model.cluster_centers_
        centroids_physical = self.scaler.inverse_transform(centroids_scaled)

        labels = self.model.labels_

        # Assign to a safe copy for counting
        counts_df = feature_df.copy()
        counts_df["regime_id"] = labels
        counts = counts_df["regime_id"].value_counts().to_dict()

        self.regimes = []
        for i in range(self.n_clusters):
            count = counts.get(i, 0)
            c = centroids_physical[i]

            summary = RegimeFeatureSummary(
                temperature_2m=float(c[0]),
                relative_humidity_2m=float(c[1]),
                precipitation=float(c[2]),
                wind_speed_10m=float(c[3]),
                cloud_cover=float(c[4]),
            )

            # Evidence-based description generated from centroids
            desc = (
                f"Temp: {c[0]:.1f}C, RH: {c[1]:.0f}%, Precip: {c[2]:.1f}mm, "
                f"Wind: {c[3]:.1f}km/h, Cloud: {c[4]:.0f}%"
            )

            reg = RegimeDefinition(
                regime_id=i,
                description=desc,
                feature_summary=summary,
                sample_count=count,
                training_period=training_period,
                model_version=f"KMeans_K{self.n_clusters}_{self.random_state}",
                provenance="ERA5_Reanalysis",
            )
            self.regimes.append(reg)

        logger.info(f"Fitted {self.n_clusters} regimes over {len(feature_df)} samples.")
        return self.regimes

    def transform(self, ref_df: pd.DataFrame) -> pd.DataFrame:
        """Assign regimes to a historical reference dataframe (validation/test)."""
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fitted before calling transform.")

        res_df = ref_df.copy()
        res_df["regime_id"] = None

        valid_mask = res_df[REFERENCE_FEATURES].notna().all(axis=1)
        if valid_mask.any():
            X = res_df.loc[valid_mask, REFERENCE_FEATURES].values
            X_scaled = self.scaler.transform(X)
            preds = self.model.predict(X_scaled)
            res_df.loc[valid_mask, "regime_id"] = preds

        return res_df

    def save(self, filepath: str) -> None:
        """Persist the fitted pipeline."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted pipeline.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(
            {
                "scaler": self.scaler,
                "model": self.model,
                "regimes": [r.model_dump() for r in self.regimes],
            },
            filepath,
        )

    @classmethod
    def load(cls, filepath: str) -> "RegimeDiscoveryPipeline":
        """Load a persisted pipeline."""
        data = joblib.load(filepath)
        pipeline = cls()
        pipeline.scaler = data["scaler"]
        pipeline.model = data["model"]
        pipeline.regimes = [RegimeDefinition(**r) for r in data["regimes"]]
        pipeline.n_clusters = pipeline.model.n_clusters
        pipeline.is_fitted = True
        return pipeline
