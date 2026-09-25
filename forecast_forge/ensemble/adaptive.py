"""Adaptive ML ensemble using Ridge Regression."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from forecast_forge.ensemble.schemas import EnsembleWeight


class AdaptiveEnsembleModel:
    """Ridge regression-based adaptive ensemble model."""

    def __init__(self, variable: str, alpha: float = 1.0, feature_config: str = "D"):
        self.variable = variable
        self.alpha = alpha
        self.feature_config = feature_config
        self.model = Ridge(alpha=self.alpha, fit_intercept=True)
        self.is_fitted = False
        self.feature_names = []
        self.models_used = []

    def _extract_features(self, df: pd.DataFrame, models: list[str]) -> pd.DataFrame:
        """Extract features for prediction based on configuration A, B, C, or D."""
        features = pd.DataFrame(index=df.index)

        # B, C, D: Model Predictions
        if self.feature_config in ["B", "C", "D"]:
            for m in models:
                col = f"{m}_{self.variable}"
                if col in df.columns:
                    features[m] = df[col]
                else:
                    features[m] = np.nan

        # A, D: Seasonal / Diurnal Context
        if self.feature_config in ["A", "D"]:
            if "valid_time" in df.columns:
                dt = pd.to_datetime(df["valid_time"])
                features["hour_sin"] = np.sin(2 * np.pi * dt.dt.hour / 24.0)
                features["hour_cos"] = np.cos(2 * np.pi * dt.dt.hour / 24.0)
                features["month_sin"] = np.sin(2 * np.pi * dt.dt.month / 12.0)
                features["month_cos"] = np.cos(2 * np.pi * dt.dt.month / 12.0)

        # C, D: Model Disagreement
        if self.feature_config in ["C", "D"]:
            model_cols = [
                f"{m}_{self.variable}" for m in models if f"{m}_{self.variable}" in df.columns
            ]
            if len(model_cols) > 0:
                features["model_spread"] = df[model_cols].std(axis=1).fillna(0.0)
            else:
                features["model_spread"] = 0.0

        # D: Legitimate Trailing Historical Skill (e.g. trailing MAE pre-calculated)
        if self.feature_config == "D":
            for m in models:
                col = f"{m}_trailing_mae"
                if col in df.columns:
                    features[f"{m}_historical_skill"] = df[col]
                else:
                    features[f"{m}_historical_skill"] = 0.0

        return features

    def fit(self, df: pd.DataFrame, models: list[str]) -> None:
        """Train the adaptive model."""
        target_col = f"ref_{self.variable}"
        if target_col not in df.columns:
            raise ValueError(f"Target column {target_col} not found in training data.")

        self.models_used = models

        # Ensure we only train on complete cases (no NaNs in target or model predictions)
        cols_to_check = [target_col] + [f"{m}_{self.variable}" for m in models]
        train_df = df.dropna(subset=[c for c in cols_to_check if c in df.columns])

        if train_df.empty:
            raise ValueError("No valid training samples available after dropping NaNs.")

        X = self._extract_features(train_df, models)

        # Drop any rows where contextual features might have introduced NaNs
        valid_idx = X.dropna().index
        X = X.loc[valid_idx]
        y = train_df.loc[valid_idx, target_col]

        self.feature_names = list(X.columns)
        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict using the trained model."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")

        X = self._extract_features(df, self.models_used)

        # Impute missing model predictions with row mean for prediction phase (robustness)
        model_cols = [c for c in X.columns if c in self.models_used]
        if len(model_cols) > 0:
            row_means = X[model_cols].mean(axis=1)
            for col in model_cols:
                X[col] = X[col].fillna(row_means)

        # Any remaining NaNs (e.g. all models missing) become 0
        X = X.fillna(0.0)

        return self.model.predict(X)

    def get_dynamic_weights(self) -> list[EnsembleWeight]:
        """Extract the model weights (coefficients) from the Ridge regression."""
        if not self.is_fitted:
            return []

        weights = []
        for feat, coef in zip(self.feature_names, self.model.coef_, strict=False):
            if feat in self.models_used:
                # We enforce non-negative weights conceptually for interpretability.
                weights.append(EnsembleWeight(model=feat, weight=max(0.0, float(coef))))

        # Normalize weights to sum to 1
        total = sum(w.weight for w in weights)
        if total > 0:
            for w in weights:
                w.weight /= total
        return weights

    def save(self, filepath: str | Path) -> None:
        """Save the model to disk."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "variable": self.variable,
                "alpha": self.alpha,
                "feature_config": self.feature_config,
                "feature_names": self.feature_names,
                "models_used": self.models_used,
                "model": self.model,
            },
            filepath,
        )

    @classmethod
    def load(cls, filepath: str | Path) -> "AdaptiveEnsembleModel":
        """Load the model from disk."""
        data = joblib.load(filepath)
        instance = cls(
            variable=data["variable"],
            alpha=data["alpha"],
            feature_config=data.get("feature_config", "D"),
        )
        instance.feature_names = data["feature_names"]
        instance.models_used = data["models_used"]
        instance.model = data["model"]
        instance.is_fitted = True
        return instance
