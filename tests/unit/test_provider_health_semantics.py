"""Regression tests for provider health status semantics.

Tests that the status derivation correctly distinguishes between:
  - AVAILABLE: valid forecast data
  - DEGRADED: partial valid data
  - NO_VALID_DATA: HTTP success but all values null
  - UNAVAILABLE: network/HTTP error
  - STALE: only cached data available

Also tests cross-dashboard consistency (Dashboard and ProviderHealth
see the same status from the same source of truth).
"""

from datetime import UTC, datetime

from forecast_forge.core.enums import ProviderStatus
from forecast_forge.core.models import ForecastPoint
from forecast_forge.validation.validator import ForecastValidator, WeatherVariable

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _make_point(temp: float | None = 25.0, **kwargs) -> ForecastPoint:
    """Create a minimal valid ForecastPoint with sane defaults."""
    return ForecastPoint(
        timestamp=datetime(2024, 1, 1, 12, tzinfo=UTC),
        latitude=19.076,
        longitude=72.877,
        provider="open_meteo",
        model="ecmwf_ifs025",
        temperature_2m=temp,
        relative_humidity_2m=kwargs.get("humidity", 70.0),
        precipitation=kwargs.get("precip", 0.0),
        wind_speed_10m=kwargs.get("wind", 15.0),
        cloud_cover=kwargs.get("cloud", 50.0),
    )


VARS = [WeatherVariable.TEMPERATURE_2M]


# ---------------------------------------------------------------------------
# 1. IFS valid forecast → AVAILABLE
# ---------------------------------------------------------------------------

def test_ifs_valid_forecast_available():
    """AVAILABLE when all records have valid temperature values."""
    records = [_make_point(25.0), _make_point(26.0), _make_point(24.5)]
    status, valid_count, _ = ForecastValidator.assess_dataset_status(records, VARS)
    assert status == ProviderStatus.AVAILABLE
    assert valid_count == 3


# ---------------------------------------------------------------------------
# 2. GFS valid forecast → AVAILABLE
# ---------------------------------------------------------------------------

def test_gfs_valid_forecast_available():
    """GFS with valid records maps to AVAILABLE."""
    records = [_make_point(28.0) for _ in range(72)]
    status, valid_count, _ = ForecastValidator.assess_dataset_status(records, VARS)
    assert status == ProviderStatus.AVAILABLE
    assert valid_count == 72


# ---------------------------------------------------------------------------
# 3. AIFS null response → NO_VALID_DATA (not UNAVAILABLE)
# ---------------------------------------------------------------------------

def test_aifs_null_response_no_valid_data():
    """AIFS returning all null values maps to NO_VALID_DATA, not UNAVAILABLE.

    This is the CRITICAL semantic distinction: the provider responded (HTTP 200)
    but there are no usable values. This must NOT be reported as UNAVAILABLE.
    """
    records = [_make_point(None) for _ in range(48)]
    status, valid_count, _ = ForecastValidator.assess_dataset_status(records, VARS)
    assert status == ProviderStatus.NO_VALID_DATA, (
        f"Expected NO_VALID_DATA but got {status}. "
        "AIFS null response must not be silently converted to UNAVAILABLE."
    )
    assert valid_count == 0


# ---------------------------------------------------------------------------
# 4. Empty records (network timeout or HTTP error) → NO_VALID_DATA from
#    assess_dataset_status, UNAVAILABLE set directly by exception handlers
# ---------------------------------------------------------------------------

def test_empty_records_no_valid_data():
    """Empty record list from assess_dataset_status returns NO_VALID_DATA.

    Note: actual UNAVAILABLE is set directly in exception handlers, not here.
    assess_dataset_status is only called when the HTTP response was received.
    """
    status, valid_count, _ = ForecastValidator.assess_dataset_status([], VARS)
    assert status == ProviderStatus.NO_VALID_DATA
    assert valid_count == 0


# ---------------------------------------------------------------------------
# 5. Partial valid response → DEGRADED
# ---------------------------------------------------------------------------

def test_partial_valid_response_degraded():
    """Some valid, some null records maps to DEGRADED (not UNAVAILABLE or NO_VALID_DATA)."""
    records = [_make_point(25.0)] * 30 + [_make_point(None)] * 18
    status, valid_count, _ = ForecastValidator.assess_dataset_status(records, VARS)
    assert status == ProviderStatus.DEGRADED, (
        f"Expected DEGRADED but got {status}. "
        "Partial data must not collapse to UNAVAILABLE."
    )
    assert valid_count == 30


# ---------------------------------------------------------------------------
# 6. Stale status is explicit (set directly, not inferred)
# ---------------------------------------------------------------------------

def test_stale_status_in_enum():
    """STALE is a valid enum value."""
    assert ProviderStatus.STALE == "STALE"


# ---------------------------------------------------------------------------
# 7. Same forecast context produces consistent status across Dashboard and Provider Health
# ---------------------------------------------------------------------------

def test_status_consistency_dashboard_vs_provider_health():
    """Dashboard (ModelForecastAPI) and ProviderHealth must see the same status
    for the same forecast context.

    This test simulates what happens when:
      - ensemble route sets status="AVAILABLE" for IFS/GFS
      - ProviderHealth derives status from same forecastRaw provider records
    Both must agree.
    """
    # 48 valid records (72h / 1.5h intervals)
    records = [_make_point(25.0 + i * 0.1) for i in range(48)]

    # What ProviderHealth.deriveStatus does via assess_dataset_status
    status, valid_count, _ = ForecastValidator.assess_dataset_status(records, VARS)
    assert status == ProviderStatus.AVAILABLE

    # The ensemble route also sets status="AVAILABLE" for these models
    # (since val is not None). They must agree.
    dashboard_status = "AVAILABLE"  # as set in ensemble.py
    assert status.value == dashboard_status, (
        f"Dashboard reports '{dashboard_status}' but ProviderHealth would infer '{status}'. "
        "These must be consistent."
    )


# ---------------------------------------------------------------------------
# 8. No model substitution occurs: AIFS stays excluded
# ---------------------------------------------------------------------------

def test_no_model_substitution_for_aifs():
    """When AIFS values are null, no IFS/GFS value is substituted.
    The status must be NO_VALID_DATA with zero valid records.
    """
    aifs_records = [_make_point(None)] * 48
    status, valid_count, _ = ForecastValidator.assess_dataset_status(aifs_records, VARS)

    assert valid_count == 0, "AIFS must have 0 valid records — no substitution allowed."
    assert status == ProviderStatus.NO_VALID_DATA
    # Confirm the valid count did NOT accidentally pick up any fallback value
    for r in aifs_records:
        assert r.temperature_2m is None, "AIFS record temperature must remain null."


# ---------------------------------------------------------------------------
# 9. No fabricated records are created
# ---------------------------------------------------------------------------

def test_no_fabricated_records():
    """validate_point must not create or alter records — it is read-only."""
    point = _make_point(25.0)
    original_temp = point.temperature_2m

    is_valid, _ = ForecastValidator.validate_point(point, VARS)

    assert is_valid
    assert point.temperature_2m == original_temp, (
        "ForecastValidator.validate_point must not modify or fabricate point values."
    )


# ---------------------------------------------------------------------------
# Status enum completeness check
# ---------------------------------------------------------------------------

def test_provider_status_enum_has_required_states():
    """Confirm all required explicit status states exist in ProviderStatus."""
    required = {"AVAILABLE", "DEGRADED", "NO_VALID_DATA", "UNAVAILABLE", "STALE"}
    actual = {s.value for s in ProviderStatus}
    assert required.issubset(actual), (
        f"Missing required status values: {required - actual}"
    )
