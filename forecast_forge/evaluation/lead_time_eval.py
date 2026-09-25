"""Exact lead-time evaluation engine with scientific causality and data-driven auditing."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_MODELS = ["ecmwf_ifs025", "gfs_seamless", "ecmwf_aifs025"]
DEFAULT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]
DEFAULT_LEAD_HOURS = [24.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0]


def audit_lead_time_dataset(
    df: pd.DataFrame,
    variables: list[str] | None = None,
    min_samples: int = 5,
    expected_models: list[str] | None = None,
    lead_hours: list[float] | None = None,
) -> pd.DataFrame:
    """Audit the actual historical dataset for every model x variable x lead_time.

    Calculates:
    - total_records
    - valid_forecast_records
    - valid_reference_records
    - valid_matched_records
    - missing_fraction
    - status ('AVAILABLE', 'INSUFFICIENT_DATA', 'UNAVAILABLE')
    """
    if variables is None:
        variables = DEFAULT_VARIABLES
    if expected_models is None:
        expected_models = DEFAULT_MODELS

    if not df.empty and "lead_time_hours" in df.columns:
        dataset_lts = sorted(df["lead_time_hours"].dropna().unique().tolist())
        target_leads = lead_hours or (dataset_lts if dataset_lts else DEFAULT_LEAD_HOURS)
    else:
        target_leads = lead_hours or DEFAULT_LEAD_HOURS

    audit_rows = []

    for var in variables:
        ref_col = f"ref_{var}"
        for lead in target_leads:
            df_lead = (
                df[df["lead_time_hours"] == lead]
                if (not df.empty and "lead_time_hours" in df.columns)
                else pd.DataFrame()
            )

            # Determine baseline total records (unique timesteps) for this lead time
            total_records = 0
            if not df_lead.empty:
                if "valid_time" in df_lead.columns:
                    total_records = int(df_lead["valid_time"].nunique())
                elif ref_col in df_lead.columns:
                    total_records = int(len(df_lead[ref_col].dropna()))

            for model in expected_models:
                m_df = (
                    df_lead[df_lead["model"] == model]
                    if (not df_lead.empty and "model" in df_lead.columns)
                    else pd.DataFrame()
                )

                if not m_df.empty:
                    m_total = len(m_df)
                    eff_total = max(total_records, m_total)
                    valid_fcst = int(m_df[var].notna().sum()) if var in m_df.columns else 0
                    valid_ref = int(m_df[ref_col].notna().sum()) if ref_col in m_df.columns else 0
                    if var in m_df.columns and ref_col in m_df.columns:
                        valid_matched = int((m_df[var].notna() & m_df[ref_col].notna()).sum())
                    else:
                        valid_matched = 0
                else:
                    eff_total = total_records
                    valid_fcst = 0
                    valid_ref = 0
                    valid_matched = 0

                missing_fraction = (
                    round(1.0 - (valid_matched / eff_total), 4) if eff_total > 0 else 1.0
                )

                if valid_matched >= min_samples:
                    status = "AVAILABLE"
                elif valid_matched > 0:
                    status = "INSUFFICIENT_DATA"
                else:
                    status = "UNAVAILABLE"

                audit_rows.append(
                    {
                        "model": model,
                        "variable": var,
                        "lead_time_hours": float(lead),
                        "total_records": eff_total,
                        "valid_forecast_records": valid_fcst,
                        "valid_reference_records": valid_ref,
                        "valid_matched_records": valid_matched,
                        "missing_fraction": missing_fraction,
                        "status": status,
                    }
                )

    return pd.DataFrame(audit_rows)


def generate_exact_lead_time_evaluation(
    df: pd.DataFrame,
    variables: list[str] | None = None,
    evaluation_mode: str = "RETROSPECTIVE",
    causal_cutoff: datetime | None = None,
    target_forecast_time: datetime | None = None,
    min_samples: int = 5,
    expected_models: list[str] | None = None,
    lead_hours: list[float] | None = None,
    epsilon: float = 1e-6,
) -> pd.DataFrame:
    """Generate exact lead-time skill evaluation and independent inverse-error weights.

    Supports:
    - evaluation_mode = 'RETROSPECTIVE': aggregates defined historical evaluation window.
    - evaluation_mode = 'CAUSAL_OPERATIONAL': strictly excludes reference or model
      data past causal_cutoff (causal_cutoff < target_forecast_time).
    """
    if evaluation_mode not in ("RETROSPECTIVE", "CAUSAL_OPERATIONAL"):
        raise ValueError(
            f"Invalid evaluation_mode '{evaluation_mode}'. Must be 'RETROSPECTIVE' "
            "or 'CAUSAL_OPERATIONAL'."
        )

    eval_df = df.copy()

    # Enforce strict operational causality if requested
    if evaluation_mode == "CAUSAL_OPERATIONAL":
        if causal_cutoff is None:
            if target_forecast_time is None:
                raise ValueError(
                    "CAUSAL_OPERATIONAL mode requires either causal_cutoff or target_forecast_time."
                )
            causal_cutoff = target_forecast_time

        if target_forecast_time is not None and causal_cutoff >= target_forecast_time:
            raise ValueError(
                f"Causality violation: causal_cutoff ({causal_cutoff}) must be strictly "
                f"before target_forecast_time ({target_forecast_time})."
            )

        if not eval_df.empty and "valid_time" in eval_df.columns:
            # Handle tz-aware vs naive timestamp comparison
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

    # Run dataset audit
    audit_df = audit_lead_time_dataset(
        df=eval_df,
        variables=variables,
        min_samples=min_samples,
        expected_models=expected_models,
        lead_hours=lead_hours,
    )

    if audit_df.empty:
        return pd.DataFrame()

    results = []

    # Calculate metrics and weights strictly independently per (variable, lead_time_hours)
    for (var, lead), group in audit_df.groupby(["variable", "lead_time_hours"]):
        ref_col = f"ref_{var}"
        df_lead = (
            eval_df[eval_df["lead_time_hours"] == lead]
            if (not eval_df.empty and "lead_time_hours" in eval_df.columns)
            else pd.DataFrame()
        )

        group_records = []
        raw_weights = {}

        for _, audit_row in group.iterrows():
            model = audit_row["model"]
            status = audit_row["status"]
            valid_matched = audit_row["valid_matched_records"]

            mae = None
            rmse = None
            bias = None

            if status == "AVAILABLE" and not df_lead.empty:
                m_df = df_lead[df_lead["model"] == model]
                if not m_df.empty and var in m_df.columns and ref_col in m_df.columns:
                    valid_mask = m_df[var].notna() & m_df[ref_col].notna()
                    matched = m_df[valid_mask]
                    if len(matched) >= min_samples:
                        errors = matched[var] - matched[ref_col]
                        mae = float(errors.abs().mean())
                        rmse = float(np.sqrt((errors**2).mean()))
                        bias = float(errors.mean())

            if status == "AVAILABLE" and rmse is not None:
                raw_weights[model] = 1.0 / (rmse + epsilon)
            else:
                raw_weights[model] = 0.0

            group_records.append(
                {
                    "model": model,
                    "variable": var,
                    "lead_time_hours": float(lead),
                    "mae": mae,
                    "rmse": rmse,
                    "bias": bias,
                    "sample_count": valid_matched,
                    "valid_samples": valid_matched,
                    "total_records": audit_row["total_records"],
                    "valid_forecast_records": audit_row["valid_forecast_records"],
                    "valid_reference_records": audit_row["valid_reference_records"],
                    "valid_matched_records": valid_matched,
                    "missing_fraction": audit_row["missing_fraction"],
                    "status": status,
                    "evaluation_mode": evaluation_mode,
                    "causal_cutoff": causal_cutoff,
                    "lead_time_semantics": "FIXED_LEAD_OFFSET",
                    "reference_source": "ERA5 reanalysis reference benchmark",
                }
            )

        # Normalize weights to sum to 1.0 across valid contributing models
        total_raw = sum(raw_weights.values())
        for rec in group_records:
            m = rec["model"]
            if total_raw > 0:
                rec["weight"] = float(raw_weights[m] / total_raw)
            else:
                rec["weight"] = 0.0
            results.append(rec)

    return pd.DataFrame(results)
