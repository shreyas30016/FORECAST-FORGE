"""Tests for multi-location validation pipeline parameterization."""

import pandas as pd
import pytest

from scripts.run_lead_time_evaluation import KNOWN_LOCATIONS


def test_city_coordinates_are_correct():
    """Verify exact coordinates specified in Phase 6.8."""
    assert KNOWN_LOCATIONS["Mumbai"].latitude == pytest.approx(19.0760)
    assert KNOWN_LOCATIONS["Mumbai"].longitude == pytest.approx(72.8777)

    assert KNOWN_LOCATIONS["Delhi"].latitude == pytest.approx(28.6139)
    assert KNOWN_LOCATIONS["Delhi"].longitude == pytest.approx(77.2090)

    assert KNOWN_LOCATIONS["Chennai"].latitude == pytest.approx(13.0827)
    assert KNOWN_LOCATIONS["Chennai"].longitude == pytest.approx(80.2707)

    assert KNOWN_LOCATIONS["Jaipur"].latitude == pytest.approx(26.9124)
    assert KNOWN_LOCATIONS["Jaipur"].longitude == pytest.approx(75.7873)

    assert KNOWN_LOCATIONS["Guwahati"].latitude == pytest.approx(26.1445)
    assert KNOWN_LOCATIONS["Guwahati"].longitude == pytest.approx(91.7362)


def test_no_location_specific_weights_hardcoded():
    """Verify that weighting logic remains agnostic to location names."""
    # We can inspect the function signature to ensure no 'location' argument is required
    import inspect

    from forecast_forge.evaluation.lead_time_eval import generate_exact_lead_time_evaluation
    sig = inspect.signature(generate_exact_lead_time_evaluation)
    assert "location" not in sig.parameters
    assert "city" not in sig.parameters


def test_missing_data_is_not_substituted():
    """Verify missing data yields UNAVAILABLE/NO_VALID_DATA rather than imputed weights."""
    from forecast_forge.evaluation.lead_time_eval import generate_exact_lead_time_evaluation

    df = pd.DataFrame() # Empty mock
    # Should safely return dataframe with UNAVAILABLE statuses without fabricating data
    res = generate_exact_lead_time_evaluation(
        df, variables=["temperature_2m"], evaluation_mode="RETROSPECTIVE"
    )
    assert not res.empty
    assert (res["status"] == "UNAVAILABLE").all()
    assert (res["weight"] == 0.0).all()


def test_causal_cutoff_logic_remains_unchanged():
    """Verify causal guard checks."""
    from datetime import UTC, datetime

    from forecast_forge.evaluation.lead_time_eval import generate_exact_lead_time_evaluation

    df = pd.DataFrame()
    with pytest.raises(ValueError, match="Causality violation"):
        generate_exact_lead_time_evaluation(
            df,
            evaluation_mode="CAUSAL_OPERATIONAL",
            causal_cutoff=datetime(2024, 1, 2, tzinfo=UTC),
            target_forecast_time=datetime(2024, 1, 1, tzinfo=UTC) # Target is before cutoff
        )
