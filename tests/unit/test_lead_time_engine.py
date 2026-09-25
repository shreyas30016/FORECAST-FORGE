"""Comprehensive scientific test suite for the Lead-Time Model Skill Engine (Phase 5E.3)."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from forecast_forge.evaluation.lead_time_eval import (
    audit_lead_time_dataset,
    generate_exact_lead_time_evaluation,
)


def _build_synthetic_dataset() -> pd.DataFrame:
    """Create a synthetic multi-model, multi-lead-time evaluation dataset."""
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, tzinfo=UTC)

    # 10 hourly timesteps
    for i in range(10):
        t = base_time + timedelta(hours=i)
        ref_temp = 20.0 + (i % 3)
        ref_precip = 0.5 * (i % 2)

        # 24h lead
        # IFS: error = +0.5 (RMSE = 0.5)
        rows.append(
            {
                "model": "ecmwf_ifs025",
                "valid_time": t,
                "lead_time_hours": 24.0,
                "temperature_2m": ref_temp + 0.5,
                "ref_temperature_2m": ref_temp,
                "precipitation": ref_precip + 0.1,
                "ref_precipitation": ref_precip,
            }
        )
        # GFS: error = +2.0 (RMSE = 2.0)
        rows.append(
            {
                "model": "gfs_seamless",
                "valid_time": t,
                "lead_time_hours": 24.0,
                "temperature_2m": ref_temp + 2.0,
                "ref_temperature_2m": ref_temp,
                "precipitation": ref_precip + 0.4,
                "ref_precipitation": ref_precip,
            }
        )
        # AIFS at 24h: valid for first 8 timesteps, error = +1.0 (RMSE = 1.0)
        aifs_val = (ref_temp + 1.0) if i < 8 else None
        rows.append(
            {
                "model": "ecmwf_aifs025",
                "valid_time": t,
                "lead_time_hours": 24.0,
                "temperature_2m": aifs_val,
                "ref_temperature_2m": ref_temp,
                "precipitation": None,
                "ref_precipitation": ref_precip,
            }
        )

        # 168h lead
        # IFS at 168h: error = +1.0
        rows.append(
            {
                "model": "ecmwf_ifs025",
                "valid_time": t,
                "lead_time_hours": 168.0,
                "temperature_2m": ref_temp + 1.0,
                "ref_temperature_2m": ref_temp,
                "precipitation": ref_precip,
                "ref_precipitation": ref_precip,
            }
        )
        # GFS at 168h: error = +3.0
        rows.append(
            {
                "model": "gfs_seamless",
                "valid_time": t,
                "lead_time_hours": 168.0,
                "temperature_2m": ref_temp + 3.0,
                "ref_temperature_2m": ref_temp,
                "precipitation": ref_precip,
                "ref_precipitation": ref_precip,
            }
        )
        # AIFS at 168h: completely missing (all None)
        rows.append(
            {
                "model": "ecmwf_aifs025",
                "valid_time": t,
                "lead_time_hours": 168.0,
                "temperature_2m": None,
                "ref_temperature_2m": ref_temp,
                "precipitation": None,
                "ref_precipitation": ref_precip,
            }
        )

    return pd.DataFrame(rows)


def test_aifs_available_on_one_lead_and_unavailable_on_another():
    """Requirement 1 & Requirement 10: AIFS available at 24h but unavailable at 168h."""
    df = _build_synthetic_dataset()
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[24.0, 168.0],
    )

    # At 24h: AIFS has 8 valid records >= min_samples 5 -> AVAILABLE
    aifs_24 = res[
        (res["model"] == "ecmwf_aifs025")
        & (res["lead_time_hours"] == 24.0)
        & (res["variable"] == "temperature_2m")
    ].iloc[0]
    assert aifs_24["status"] == "AVAILABLE"
    assert aifs_24["weight"] > 0.0
    assert aifs_24["rmse"] is not None

    # At 168h: AIFS has 0 valid records -> UNAVAILABLE with 0 weight
    aifs_168 = res[
        (res["model"] == "ecmwf_aifs025")
        & (res["lead_time_hours"] == 168.0)
        & (res["variable"] == "temperature_2m")
    ].iloc[0]
    assert aifs_168["status"] == "UNAVAILABLE"
    assert aifs_168["weight"] == 0.0
    assert pd.isna(aifs_168["rmse"])


def test_aifs_valid_record_detection():
    """Requirement 2: Accurate detection of forecast, reference, and matched counts."""
    df = _build_synthetic_dataset()
    audit = audit_lead_time_dataset(
        df,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[24.0],
    )

    aifs_audit = audit[
        (audit["model"] == "ecmwf_aifs025") & (audit["lead_time_hours"] == 24.0)
    ].iloc[0]
    assert aifs_audit["total_records"] == 10
    assert aifs_audit["valid_forecast_records"] == 8
    assert aifs_audit["valid_reference_records"] == 10
    assert aifs_audit["valid_matched_records"] == 8
    assert aifs_audit["missing_fraction"] == 0.2
    assert aifs_audit["status"] == "AVAILABLE"


def test_minimum_sample_threshold():
    """Requirement 3: Distinguish AVAILABLE, INSUFFICIENT_DATA, and UNAVAILABLE."""
    df = _build_synthetic_dataset()

    # Threshold = 5: AIFS with 8 samples is AVAILABLE
    res_avail = generate_exact_lead_time_evaluation(
        df, variables=["temperature_2m"], min_samples=5, lead_hours=[24.0]
    )
    aifs_avail = res_avail[res_avail["model"] == "ecmwf_aifs025"].iloc[0]
    assert aifs_avail["status"] == "AVAILABLE"

    # Threshold = 10: AIFS with 8 samples is INSUFFICIENT_DATA (0 < 8 < 10)
    res_insuf = generate_exact_lead_time_evaluation(
        df, variables=["temperature_2m"], min_samples=10, lead_hours=[24.0]
    )
    aifs_insuf = res_insuf[res_insuf["model"] == "ecmwf_aifs025"].iloc[0]
    assert aifs_insuf["status"] == "INSUFFICIENT_DATA"
    assert aifs_insuf["weight"] == 0.0
    assert pd.isna(aifs_insuf["rmse"])

    # Threshold = 5 at 168h: AIFS with 0 samples is UNAVAILABLE
    res_unavail = generate_exact_lead_time_evaluation(
        df, variables=["temperature_2m"], min_samples=5, lead_hours=[168.0]
    )
    aifs_unavail = res_unavail[res_unavail["model"] == "ecmwf_aifs025"].iloc[0]
    assert aifs_unavail["status"] == "UNAVAILABLE"
    assert aifs_unavail["weight"] == 0.0


def test_retrospective_evaluation():
    """Requirement 4: Retrospective evaluation aggregates defined historical period."""
    df = _build_synthetic_dataset()
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        evaluation_mode="RETROSPECTIVE",
        lead_hours=[24.0],
    )
    assert not res.empty
    assert (res["evaluation_mode"] == "RETROSPECTIVE").all()
    # All 10 timesteps used for IFS
    ifs = res[res["model"] == "ecmwf_ifs025"].iloc[0]
    assert ifs["valid_samples"] == 10
    assert ifs["mae"] == 0.5


def test_causal_operational_cutoff():
    """Requirement 5: Operational mode applies cutoff strictly before target forecast."""
    df = _build_synthetic_dataset()
    base_time = datetime(2024, 6, 1, 0, 0, tzinfo=UTC)
    cutoff = base_time + timedelta(hours=4)  # include timesteps 0, 1, 2, 3, 4 (5 records)
    target = base_time + timedelta(hours=10)

    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        evaluation_mode="CAUSAL_OPERATIONAL",
        causal_cutoff=cutoff,
        target_forecast_time=target,
        min_samples=5,
        lead_hours=[24.0],
    )

    assert not res.empty
    assert (res["evaluation_mode"] == "CAUSAL_OPERATIONAL").all()
    ifs = res[res["model"] == "ecmwf_ifs025"].iloc[0]
    assert ifs["valid_samples"] == 5


def test_future_record_exclusion():
    """Requirement 6: Future records past causal cutoff must NOT leak into weights."""
    df_past = _build_synthetic_dataset()
    base_time = datetime(2024, 6, 1, 0, 0, tzinfo=UTC)
    cutoff = base_time + timedelta(hours=5)
    target = base_time + timedelta(hours=12)

    res_clean = generate_exact_lead_time_evaluation(
        df_past,
        variables=["temperature_2m"],
        evaluation_mode="CAUSAL_OPERATIONAL",
        causal_cutoff=cutoff,
        target_forecast_time=target,
        min_samples=5,
        lead_hours=[24.0],
    )
    weight_clean = res_clean[res_clean["model"] == "ecmwf_ifs025"].iloc[0]["weight"]

    # Append drastic future errors (error = 100.0) at T + 20h
    df_with_future = df_past.copy()
    future_time = base_time + timedelta(hours=20)
    for model in ["ecmwf_ifs025", "gfs_seamless", "ecmwf_aifs025"]:
        df_with_future = pd.concat(
            [
                df_with_future,
                pd.DataFrame(
                    [
                        {
                            "model": model,
                            "valid_time": future_time,
                            "lead_time_hours": 24.0,
                            "temperature_2m": 120.0,
                            "ref_temperature_2m": 20.0,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    res_future_guarded = generate_exact_lead_time_evaluation(
        df_with_future,
        variables=["temperature_2m"],
        evaluation_mode="CAUSAL_OPERATIONAL",
        causal_cutoff=cutoff,
        target_forecast_time=target,
        min_samples=5,
        lead_hours=[24.0],
    )
    weight_guarded = res_future_guarded[res_future_guarded["model"] == "ecmwf_ifs025"].iloc[0][
        "weight"
    ]

    # Weight MUST be exactly identical: future corrupted records completely excluded
    assert weight_clean == weight_guarded

    # Test causality check: cutoff >= target must raise ValueError
    with pytest.raises(ValueError, match="Causality violation"):
        generate_exact_lead_time_evaluation(
            df_past,
            evaluation_mode="CAUSAL_OPERATIONAL",
            causal_cutoff=target,
            target_forecast_time=target,
        )


def test_per_lead_independent_weights():
    """Requirement 7: Weights at 24h are calculated independently from weights at 168h."""
    df = _build_synthetic_dataset()
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[24.0, 168.0],
    )

    ifs_24_weight = res[(res["model"] == "ecmwf_ifs025") & (res["lead_time_hours"] == 24.0)].iloc[
        0
    ]["weight"]
    ifs_168_weight = res[(res["model"] == "ecmwf_ifs025") & (res["lead_time_hours"] == 168.0)].iloc[
        0
    ]["weight"]

    # At 24h: 3 models compete (IFS, GFS, AIFS)
    # At 168h: only 2 models compete (IFS, GFS) because AIFS is unavailable
    assert ifs_24_weight != ifs_168_weight


def test_sum_to_one_normalization():
    """Requirement 8: Valid contributing model weights sum to 1.0 at every lead time."""
    df = _build_synthetic_dataset()
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[24.0, 168.0],
    )

    for lead in [24.0, 168.0]:
        lead_res = res[res["lead_time_hours"] == lead]
        valid_weights = lead_res[lead_res["status"] == "AVAILABLE"]["weight"]
        assert abs(valid_weights.sum() - 1.0) < 1e-4


def test_unavailable_model_zero_weight_and_single_valid():
    """Requirement 9: Unavailable models receive 0.0; single valid model receives 1.0."""
    df = _build_synthetic_dataset()
    # At 168h, AIFS is unavailable
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[168.0],
    )
    aifs = res[res["model"] == "ecmwf_aifs025"].iloc[0]
    assert aifs["weight"] == 0.0

    # If only 1 model is available (filter dataset to only IFS)
    only_ifs = df[df["model"] == "ecmwf_ifs025"]
    res_single = generate_exact_lead_time_evaluation(
        only_ifs,
        variables=["temperature_2m"],
        min_samples=5,
        lead_hours=[24.0],
    )
    ifs_single = res_single[res_single["model"] == "ecmwf_ifs025"].iloc[0]
    assert ifs_single["weight"] == 1.0


def test_provenance_preservation():
    """Requirement 10: Semantics and reference source preserved without fabrication."""
    df = _build_synthetic_dataset()
    res = generate_exact_lead_time_evaluation(
        df,
        variables=["temperature_2m"],
        lead_hours=[24.0],
    )
    for _, row in res.iterrows():
        assert row["lead_time_semantics"] == "FIXED_LEAD_OFFSET"
        assert row["reference_source"] == "ERA5 reanalysis reference benchmark"
