import uuid
from datetime import UTC, datetime

import pytest

from forecast_forge.agent.runtime import AgentRuntime
from forecast_forge.agent.schemas import AgentChatRequest, AgentContext, ChatMessage
from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import Location
from forecast_forge.trace.schemas import (
    BustTrace,
    DecisionTrace,
    ExtremeGuidanceTrace,
    ProbabilisticTrace,
    RegimeTrace,
    TraceContext,
    TraceForecast,
    VerificationTrace,
    WeightEvidence,
)
from forecast_forge.trace.storage import TraceStorage


@pytest.fixture
def test_trace():
    trace_id = str(uuid.uuid4())
    context = TraceContext(
        variable=WeatherVariable.TEMPERATURE_2M,
        valid_time=datetime.now(UTC),
        lead_time_hours=72,
        forecast_run=datetime.now(UTC),
    )

    forecast = TraceForecast(
        value=25.5,
        unit="metric",
        status="OK",
        source="Blended Ensemble",
        valid_time=datetime.now(UTC),
        provenance="Blended Ensemble"
    )

    weights = [
        WeightEvidence(
            model="ecmwf_ifs025",
            weight=0.73,
            weight_method="historical",
            rmse=0.5,
            status="AVAILABLE",
            provenance="Test"
        ),
        WeightEvidence(
            model="gfs_seamless",
            weight=0.27,
            weight_method="historical",
            rmse=1.5,
            status="AVAILABLE",
            provenance="Test"
        ),
    ]

    trace = DecisionTrace(
        trace_id=trace_id,
        created_at=datetime.now(UTC),
        location=Location(name="Mumbai", latitude=19.06, longitude=72.93),
        request_context=context,
        decision_integrity="VERIFIED",
        forecast=forecast,
        model_inputs={},
        weights=weights,
        regime=RegimeTrace(
            regime_id=1, description="Stable", status="AVAILABLE", provenance="Test"
        ),
        probabilistic=ProbabilisticTrace(
            model="Blended",
            member_count=50,
            valid_member_count=50,
            status="AVAILABLE",
            provenance="Test"
        ),
        extreme_guidance=[
            ExtremeGuidanceTrace(
                event_type="Heatwave",
                variable="temperature_2m",
                operator=">",
                threshold=35.0,
                probability=0.0,
                status="AVAILABLE",
                provenance="Test"
            )
        ],
        bust_signal=BustTrace(signal="NONE", status="AVAILABLE", provenance="Test"),
        verification=VerificationTrace(reference_source="ERA5", status="PENDING"),
        limitations=[]
    )

    storage = TraceStorage()
    storage.save_trace(trace)
    return trace


def test_agent_explains_weights_with_full_context(test_trace):
    runtime = AgentRuntime()
    if not runtime.provider:
        pytest.skip("No provider available (missing API keys)")

    request = AgentChatRequest(
        messages=[ChatMessage(role="user", content="Explain these weights")],
        context=AgentContext(
            location="Mumbai",
            latitude=19.06,
            longitude=72.93,
            lead_time_hours=72,
            variable="temperature_2m",
            trace_id=test_trace.trace_id,
        )
    )

    response = runtime.run(request)

    # The agent should have used the get_decision_trace tool
    assert any(activity["tool"] == "get_decision_trace" for activity in response.tool_activity)

    # The response should mention the weights from the trace
    content_lower = response.response.lower()
    assert "73" in content_lower or "ecmwf" in content_lower
    assert "27" in content_lower or "gfs" in content_lower


def test_agent_refuses_to_invent_weights_missing_trace():
    runtime = AgentRuntime()
    if not runtime.provider:
        pytest.skip("No provider available (missing API keys)")

    request = AgentChatRequest(
        messages=[ChatMessage(role="user", content="Explain these weights")],
        context=AgentContext(
            location="Mumbai",
            latitude=19.06,
            longitude=72.93,
            lead_time_hours=72,
            variable="temperature_2m",
            trace_id="invalid-trace-id-12345",
        )
    )

    response = runtime.run(request)

    # The agent should call the tool and fail
    assert any(activity["tool"] == "get_decision_trace" for activity in response.tool_activity)

    # The response should refuse nicely
    content_lower = response.response.lower()
    assert (
        "unavailable" in content_lower
        or "cannot" in content_lower
        or "not found" in content_lower
    )
