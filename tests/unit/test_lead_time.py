"""Tests for lead time, leakage protection, and provider lead-time parsing."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from forecast_forge.api.schemas import EvaluationResponse, ModelSkillRecord
from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastPoint, HistoricalRequest, Location
from forecast_forge.evaluation.lead_time import assign_lead_time_bucket, calculate_lead_time_hours
from forecast_forge.providers.open_meteo.ifs import ECMWFIFSProvider


def test_calculate_lead_time_valid():
    df = pd.DataFrame(
        {
            "initialization_time": [datetime(2023, 1, 1, 0, tzinfo=UTC)],
            "valid_time": [datetime(2023, 1, 1, 12, tzinfo=UTC)],
        }
    )
    lt = calculate_lead_time_hours(df)
    assert lt.iloc[0] == 12.0


def test_calculate_lead_time_leakage():
    df = pd.DataFrame(
        {
            "initialization_time": [datetime(2023, 1, 1, 12, tzinfo=UTC)],
            "valid_time": [datetime(2023, 1, 1, 0, tzinfo=UTC)],
        }
    )
    with pytest.raises(ValueError, match="leakage"):
        calculate_lead_time_hours(df)


def test_forecast_point_causality_rejection():
    """Ensure ForecastPoint rejects negative leads / temporal causality violations."""
    init_dt = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    invalid_valid_dt = datetime(2026, 9, 20, 6, 0, tzinfo=UTC)  # 6 hours BEFORE init!

    with pytest.raises(ValueError, match="Causality violation"):
        ForecastPoint(
            timestamp=invalid_valid_dt,
            latitude=19.076,
            longitude=72.8777,
            temperature_2m=25.0,
            provider="Open-Meteo",
            model="ecmwf_ifs025",
            initialization_time=init_dt,
            lead_time_hours=-6.0,
        )


def test_assign_lead_time_bucket():
    lt = pd.Series([3.0, 8.0, 25.0, 48.0, 72.0, 120.0, 168.0])
    buckets = assign_lead_time_bucket(lt)
    assert buckets.iloc[0] == "0-6h"
    assert buckets.iloc[1] == "6-12h"
    assert buckets.iloc[2] == "24-48h"
    assert buckets.iloc[3] == "48-72h"
    assert buckets.iloc[4] == "72-120h"
    assert buckets.iloc[5] == "120-168h"
    assert buckets.iloc[6] == "168h+"


def test_previous_runs_fixed_lead_mapping():
    """Verify Previous Runs parsing: day1 -> 24h ... day7 -> 168h (anti-fabrication)."""
    provider = ECMWFIFSProvider()
    req = HistoricalRequest(
        location=Location(latitude=19.076, longitude=72.8777),
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 1),
        variables=[WeatherVariable.TEMPERATURE_2M],
        lead_time_days=[1, 2, 3, 4, 5, 6, 7],
    )

    mock_data = {
        "hourly": {
            "time": ["2024-06-01T00:00"],
            "temperature_2m_previous_day1": [25.1],
            "temperature_2m_previous_day2": [25.2],
            "temperature_2m_previous_day3": [25.3],
            "temperature_2m_previous_day4": [25.4],
            "temperature_2m_previous_day5": [25.5],
            "temperature_2m_previous_day6": [25.6],
            "temperature_2m_previous_day7": [25.7],
        },
        "hourly_units": {"temperature_2m": "°C"},
    }

    result = provider._parse_previous_runs_response(
        data=mock_data,
        request=req,
        status_code=200,
        request_timestamp=datetime.now(UTC),
        latency_ms=10.0,
    )

    assert result.status.value == "AVAILABLE"
    assert len(result.records) == 7

    expected_leads = {
        1: 24.0,
        2: 48.0,
        3: 72.0,
        4: 96.0,
        5: 120.0,
        6: 144.0,
        7: 168.0,
    }

    for idx, (day, expected_lead) in enumerate(expected_leads.items()):
        rec = result.records[idx]
        assert rec.lead_time_hours == expected_lead
        assert rec.initialization_time is None  # Anti-fabrication rule: un-invented initialization
        assert rec.lead_time_semantics == "FIXED_LEAD_OFFSET"
        assert rec.provenance_source == f"open_meteo_previous_runs_day{day}"
        assert rec.temperature_2m == pytest.approx(25.0 + day * 0.1, 0.01)


def test_single_runs_exact_cycle_parsing():
    """Verify Single Runs parsing: exact init timestamp, exact lead calculation, causality check."""
    provider = ECMWFIFSProvider()
    init_time = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
    req = HistoricalRequest(
        location=Location(latitude=19.076, longitude=72.8777),
        start_date=date(2026, 9, 20),
        end_date=date(2026, 9, 21),
        run=init_time,
        variables=[WeatherVariable.TEMPERATURE_2M],
    )

    mock_data = {
        "hourly": {
            "time": [
                "2026-09-19T23:00",  # Prior to run - should be rejected by causality filter!
                "2026-09-20T00:00",  # Lead 0h
                "2026-09-20T06:00",  # Lead 6h
                "2026-09-21T00:00",  # Lead 24h
            ],
            "temperature_2m": [24.0, 25.0, 26.5, 27.0],
        },
        "hourly_units": {"temperature_2m": "°C"},
    }

    result = provider._parse_single_run_response(
        data=mock_data,
        request=req,
        status_code=200,
        request_timestamp=datetime.now(UTC),
        latency_ms=15.0,
    )

    assert result.status.value == "AVAILABLE"
    # The record prior to initialization must be filtered out by causality guard
    assert len(result.records) == 3

    r0 = result.records[0]
    assert r0.timestamp == datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
    assert r0.initialization_time == init_time
    assert r0.lead_time_hours == 0.0
    assert r0.lead_time_semantics == "EXACT_RUN_CYCLE"
    assert r0.provenance_source == "open_meteo_single_runs"

    r1 = result.records[1]
    assert r1.timestamp == datetime(2026, 9, 20, 6, 0, tzinfo=UTC)
    assert r1.lead_time_hours == 6.0

    r2 = result.records[2]
    assert r2.timestamp == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
    assert r2.lead_time_hours == 24.0


def test_evaluation_response_capability_flag():
    """Verify data-driven capability reporting in EvaluationResponse."""
    # Case 1: No lead-time records present -> lead_time_available must be False
    records_aggregate = [
        ModelSkillRecord(
            model="ecmwf_ifs025",
            variable="temperature_2m",
            lead_time_hours=None,
            sample_count=100,
            evaluation_period="All (Aggregate)",
            status="AVAILABLE",
        )
    ]
    has_lt_1 = any(
        r.lead_time_hours is not None for r in records_aggregate if r.status == "AVAILABLE"
    )
    resp_1 = EvaluationResponse(lead_time_available=has_lt_1, evaluations=records_aggregate)
    assert resp_1.lead_time_available is False

    # Case 2: Fixed-lead records present -> lead_time_available must be True
    records_fixed_lead = [
        ModelSkillRecord(
            model="ecmwf_ifs025",
            variable="temperature_2m",
            lead_time_hours=24.0,
            sample_count=100,
            evaluation_period="24-48h",
            status="AVAILABLE",
            lead_time_semantics="FIXED_LEAD_OFFSET",
        )
    ]
    has_lt_2 = any(
        r.lead_time_hours is not None for r in records_fixed_lead if r.status == "AVAILABLE"
    )
    resp_2 = EvaluationResponse(lead_time_available=has_lt_2, evaluations=records_fixed_lead)
    assert resp_2.lead_time_available is True

    # Case 3: Run-aware records present -> lead_time_available must be True
    records_run_aware = [
        ModelSkillRecord(
            model="ecmwf_ifs025",
            variable="temperature_2m",
            lead_time_hours=48.0,
            sample_count=100,
            evaluation_period="48-72h",
            status="AVAILABLE",
            initialization_time=datetime(2026, 9, 20, 0, 0, tzinfo=UTC),
            lead_time_semantics="EXACT_RUN_CYCLE",
        )
    ]
    has_lt_3 = any(
        r.lead_time_hours is not None for r in records_run_aware if r.status == "AVAILABLE"
    )
    resp_3 = EvaluationResponse(lead_time_available=has_lt_3, evaluations=records_run_aware)
    assert resp_3.lead_time_available is True
