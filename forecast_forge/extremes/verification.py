"""Verification module for extreme weather events against ERA5 reanalysis reference benchmark."""

import numpy as np

from forecast_forge.extremes.schemas import EventVerificationResult


class ExtremesVerification:
    """Historical verification of extreme events."""

    @staticmethod
    def calculate_brier_score(
        forecast_probs: np.ndarray, observed_events: np.ndarray
    ) -> float | None:
        """
        Calculate Brier Score.
        BS = 1/N * sum((f - o)^2)
        """
        if len(forecast_probs) == 0 or len(forecast_probs) != len(observed_events):
            return None

        return float(np.mean((forecast_probs - observed_events) ** 2))

    @staticmethod
    def calculate_categorical_metrics(
        forecast_probs: np.ndarray, observed_events: np.ndarray, prob_threshold: float = 0.5
    ) -> dict[str, float | None]:
        """
        Calculate Probability of Detection (POD), False Alarm Ratio (FAR),
        and Critical Success Index (CSI) for a given probability threshold.
        """
        if len(forecast_probs) == 0 or len(forecast_probs) != len(observed_events):
            return {"pod": None, "far": None, "csi": None}

        forecast_events = (forecast_probs >= prob_threshold).astype(int)

        hits = np.sum((forecast_events == 1) & (observed_events == 1))
        misses = np.sum((forecast_events == 0) & (observed_events == 1))
        false_alarms = np.sum((forecast_events == 1) & (observed_events == 0))

        pod = hits / (hits + misses) if (hits + misses) > 0 else None
        far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else None
        csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else None

        return {
            "pod": float(pod) if pod is not None else None,
            "far": float(far) if far is not None else None,
            "csi": float(csi) if csi is not None else None,
        }

    @classmethod
    def verify_event(
        cls,
        event_type: str,
        threshold: float,
        model: str,
        lead_time_hours: int,
        forecast_probs: list[float],
        observed_events: list[int],
    ) -> EventVerificationResult:
        """Verify an event across a dataset of forecasts vs observations."""

        f_arr = np.array(forecast_probs)
        o_arr = np.array(observed_events)

        bs = cls.calculate_brier_score(f_arr, o_arr)
        cat_metrics = cls.calculate_categorical_metrics(f_arr, o_arr)

        return EventVerificationResult(
            event_type=event_type,
            threshold=threshold,
            model=model,
            lead_time_hours=lead_time_hours,
            sample_size=len(f_arr),
            brier_score=bs,
            pod=cat_metrics["pod"],
            far=cat_metrics["far"],
            csi=cat_metrics["csi"],
            reference="ERA5 reanalysis reference benchmark",
        )
