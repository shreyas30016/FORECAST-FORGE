"""Regime-conditioned model skill evaluation."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from forecast_forge.evaluation.lead_time_eval import (
    DEFAULT_LEAD_HOURS,
    DEFAULT_MODELS,
    DEFAULT_VARIABLES,
)
from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)


def generate_regime_conditioned_skill(
    df: pd.DataFrame,
    variables: list[str] | None = None,
    evaluation_mode: str = "RETROSPECTIVE",
    causal_cutoff: datetime | None = None,
    min_samples: int = 5,
    expected_models: list[str] | None = None,
    lead_hours: list[float] | None = None,
    epsilon: float = 1e-6,
) -> pd.DataFrame:
    """Generate regime x lead-time skill evaluation and independent inverse-error weights."""

    if evaluation_mode not in ("RETROSPECTIVE", "CAUSAL_OPERATIONAL"):
        raise ValueError("Invalid evaluation_mode")

    eval_df = df.copy()

    # Enforce strict operational causality if requested
    if evaluation_mode == "CAUSAL_OPERATIONAL" and causal_cutoff is not None:
        if not eval_df.empty and "valid_time" in eval_df.columns:
            first_time = eval_df["valid_time"].iloc[0]
            if isinstance(first_time, str):
                eval_df["valid_time"] = pd.to_datetime(eval_df["valid_time"])
                first_time = eval_df["valid_time"].iloc[0]

            is_df_tz = getattr(first_time, "tzinfo", None) is not None
            if is_df_tz and causal_cutoff.tzinfo is None:
                cutoff_cmp = causal_cutoff.replace(tzinfo=UTC)
            elif not is_df_tz and causal_cutoff.tzinfo is not None:
                cutoff_cmp = causal_cutoff.replace(tzinfo=None)
            else:
                cutoff_cmp = causal_cutoff

            eval_df = eval_df[eval_df["valid_time"] <= cutoff_cmp].copy()

    if variables is None:
        variables = DEFAULT_VARIABLES
    if expected_models is None:
        expected_models = DEFAULT_MODELS
    if lead_hours is None:
        if not eval_df.empty and "lead_time_hours" in eval_df.columns:
            dataset_lts = sorted(eval_df["lead_time_hours"].dropna().unique().tolist())
            lead_hours = dataset_lts if dataset_lts else DEFAULT_LEAD_HOURS
        else:
            lead_hours = DEFAULT_LEAD_HOURS

    if eval_df.empty or "regime_id" not in eval_df.columns:
        return pd.DataFrame()

    results = []

    # Group strictly by regime_id and lead_time_hours
    regimes = eval_df["regime_id"].dropna().unique().tolist()

    for var in variables:
        ref_col = f"ref_{var}"
        for lead in lead_hours:
            for regime in regimes:
                # Isolate the exact slice
                slice_df = eval_df[
                    (eval_df["lead_time_hours"] == lead) & (eval_df["regime_id"] == regime)
                ]

                group_records = []
                raw_weights = {}

                total_records = 0
                if not slice_df.empty:
                    if "valid_time" in slice_df.columns:
                        total_records = int(slice_df["valid_time"].nunique())
                    elif ref_col in slice_df.columns:
                        total_records = int(len(slice_df[ref_col].dropna()))

                for model in expected_models:
                    m_df = (
                        slice_df[slice_df["model"] == model]
                        if not slice_df.empty
                        else pd.DataFrame()
                    )

                    m_total = len(m_df)
                    eff_total = max(total_records, m_total)

                    valid_matched = 0
                    mae = None
                    rmse = None
                    bias = None

                    if not m_df.empty and var in m_df.columns and ref_col in m_df.columns:
                        valid_mask = m_df[var].notna() & m_df[ref_col].notna()
                        matched = m_df[valid_mask]
                        valid_matched = len(matched)

                        if valid_matched >= min_samples:
                            errors = matched[var] - matched[ref_col]
                            mae = float(errors.abs().mean())
                            rmse = float(np.sqrt((errors**2).mean()))
                            bias = float(errors.mean())
                            status = "AVAILABLE"
                        elif valid_matched > 0:
                            status = "INSUFFICIENT_DATA"
                        else:
                            status = "UNAVAILABLE"
                    else:
                        status = "UNAVAILABLE"

                    missing_fraction = (
                        round(1.0 - (valid_matched / eff_total), 4) if eff_total > 0 else 1.0
                    )

                    if status == "AVAILABLE" and rmse is not None:
                        raw_weights[model] = 1.0 / (rmse + epsilon)
                    else:
                        raw_weights[model] = 0.0

                    group_records.append(
                        {
                            "regime_id": int(regime),
                            "model": model,
                            "variable": var,
                            "lead_time_hours": float(lead),
                            "mae": mae,
                            "rmse": rmse,
                            "bias": bias,
                            "sample_count": valid_matched,
                            "missing_fraction": missing_fraction,
                            "status": status,
                            "evaluation_mode": evaluation_mode,
                        }
                    )

                total_raw = sum(raw_weights.values())
                for rec in group_records:
                    m = rec["model"]
                    rec["weight"] = float(raw_weights[m] / total_raw) if total_raw > 0 else 0.0
                    results.append(rec)

    return pd.DataFrame(results)
