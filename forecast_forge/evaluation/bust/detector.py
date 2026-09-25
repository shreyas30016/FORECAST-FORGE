"""Detector for forecasting large errors (busts) using causal features."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class ForecastBustDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.numeric_features = [
            "lead_time_hours",
            "model_disagreement",
            "within_model_ensemble_spread",
            "valid_member_count",
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
        ]
        self.categorical_features = ["regime_id"]

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), self.numeric_features),
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    self.categorical_features,
                ),
            ],
            remainder="drop",
        )
        self.thresholds = {}  # (variable, lead_time) -> error_threshold
        self.quantile = 0.90

    def fit(self, df: pd.DataFrame, variable: str, quantile: float = 0.90):
        self.quantile = quantile
        # df must contain causal features, the blended target forecast, and the ref value

        # Calculate thresholds purely on train set by lead time
        train_df = df.copy()
        train_df["abs_error"] = (train_df["target_forecast"] - train_df[f"ref_{variable}"]).abs()

        for lead in train_df["lead_time_hours"].unique():
            lead_df = train_df[train_df["lead_time_hours"] == lead]
            if len(lead_df) > 0:
                self.thresholds[(variable, lead)] = lead_df["abs_error"].quantile(self.quantile)

        # Label events
        train_df["bust_label"] = 0
        for lead in train_df["lead_time_hours"].unique():
            thresh = self.thresholds.get((variable, lead), float("inf"))
            mask = (train_df["lead_time_hours"] == lead) & (train_df["abs_error"] > thresh)
            train_df.loc[mask, "bust_label"] = 1

        for col in self.numeric_features + self.categorical_features:
            if col not in train_df.columns:
                train_df[col] = 0.0

        train_df = train_df.dropna(subset=self.numeric_features + self.categorical_features)
        if len(train_df) == 0:
            return

        X = train_df[self.numeric_features + self.categorical_features].copy()
        y = train_df["bust_label"].values

        self.scaler = self.preprocessor
        X_scaled = self.scaler.fit_transform(X)

        cat_names = self.scaler.named_transformers_["cat"].get_feature_names_out(
            self.categorical_features
        )
        self.feature_names_out = list(self.numeric_features) + list(cat_names)

        # Logistic Regression with class weights
        if len(np.unique(y)) > 1:
            self.model = LogisticRegression(class_weight="balanced", random_state=42)
            self.model.fit(X_scaled, y)

    def predict_signal(self, features: dict, variable: str) -> tuple[str, list, float]:
        if not self.model or not self.scaler:
            return "INSUFFICIENT_DATA", [], 0.0

        lead = features.get("lead_time_hours", 72)
        thresh = self.thresholds.get((variable, lead), 0.0)

        X_df = pd.DataFrame([features])
        for f in self.numeric_features + self.categorical_features:
            if f not in X_df.columns:
                if f == "regime_id":
                    X_df[f] = -1
                else:
                    X_df[f] = 0.0

        X_df = X_df[self.numeric_features + self.categorical_features]
        X_scaled = self.scaler.transform(X_df)

        pred = self.model.predict(X_scaled)[0]

        # Explainability
        coefs = self.model.coef_[0]
        contributions = coefs * X_scaled[0]

        factors = []
        for name, contrib in zip(self.feature_names_out, contributions, strict=False):
            if abs(contrib) > 0.05:
                direction = "POSITIVE" if contrib > 0 else "NEGATIVE"
                factors.append(
                    {"name": name, "contribution": float(abs(contrib)), "direction": direction}
                )

        factors = sorted(factors, key=lambda x: x["contribution"], reverse=True)[:5]

        signal = "ELEVATED" if pred == 1 else "NORMAL"
        return signal, factors, thresh

    def save(self, path: str):
        import joblib

        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "thresholds": self.thresholds,
                "quantile": self.quantile,
                "feature_names_out": getattr(self, "feature_names_out", []),
            },
            path,
        )

    @classmethod
    def load(cls, path: str):
        import joblib

        inst = cls()
        data = joblib.load(path)
        inst.model = data["model"]
        inst.scaler = data["scaler"]
        inst.thresholds = data["thresholds"]
        inst.quantile = data["quantile"]
        inst.feature_names_out = data.get("feature_names_out", [])
        return inst
