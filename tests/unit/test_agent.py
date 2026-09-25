from unittest.mock import MagicMock, patch

import pytest

from forecast_forge.agent.runtime import AgentRuntime
from forecast_forge.agent.schemas import AgentChatRequest, AgentContext, ChatMessage


@pytest.fixture
def mock_settings():
    with patch("forecast_forge.agent.providers.nemotron.get_settings") as mock:
        settings = MagicMock()
        settings.nvidia_api_key = "test_key"
        settings.nvidia_base_url = "http://test"
        settings.nvidia_model = "test-model"
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_openai():
    with patch("forecast_forge.agent.providers.nemotron.OpenAI") as mock:
        yield mock


def test_agent_runtime_init(mock_settings, mock_openai):
    runtime = AgentRuntime()
    assert runtime.provider is not None
    mock_openai.assert_called_once_with(base_url="http://test", api_key="test_key")


def test_agent_runtime_missing_key():
    with patch("forecast_forge.agent.providers.nemotron.get_settings") as mock:
        settings = MagicMock()
        settings.nvidia_api_key = None
        mock.return_value = settings

        runtime = AgentRuntime()
        assert runtime.provider is None

        with pytest.raises(ValueError):
            runtime.run(AgentChatRequest(messages=[]))


def test_agent_runtime_basic_chat(mock_settings, mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.content = "I am a forecast copilot."
    mock_client.chat.completions.create.return_value = mock_response

    runtime = AgentRuntime()
    req = AgentChatRequest(messages=[ChatMessage(role="user", content="Hello")])
    res = runtime.run(req)

    assert res.response == "I am a forecast copilot."
    assert len(res.tool_activity) == 0


def test_agent_runtime_tool_call(mock_settings, mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # First iteration: returns a tool call
    mock_tool_call_response = MagicMock()
    mock_tool_call_response.choices = [MagicMock()]
    mock_message = mock_tool_call_response.choices[0].message
    mock_message.content = None

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_1"
    mock_tool_call.function.name = "get_decision_trace"
    mock_tool_call.function.arguments = '{"latitude": 10.0, "longitude": 20.0}'
    mock_message.tool_calls = [mock_tool_call]
    mock_message.model_dump.return_value = {"role": "assistant", "tool_calls": [{"id": "call_1"}]}

    # Second iteration: returns text
    mock_text_response = MagicMock()
    mock_text_response.choices = [MagicMock()]
    mock_text_response.choices[0].message.tool_calls = None
    mock_text_response.choices[0].message.content = "Tool executed successfully."

    mock_client.chat.completions.create.side_effect = [mock_tool_call_response, mock_text_response]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_registry:
        mock_registry.__contains__.return_value = True
        mock_registry.__getitem__.return_value = MagicMock(return_value={"status": "AVAILABLE"})

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="Check trace")],
            context=AgentContext(latitude=10.0, longitude=20.0),
        )
        res = runtime.run(req)

        assert res.response == "Tool executed successfully."
        assert len(res.tool_activity) == 1
        assert res.tool_activity[0]["tool"] == "get_decision_trace"
        assert res.tool_activity[0]["args"] == {"latitude": 10.0, "longitude": 20.0}


# ==============================================================================
# PHASE 6.2.2 PART 10 DETERMINISTIC SCENARIO TESTS (A - H)
# ==============================================================================


def _make_mock_tool_call(call_id: str, name: str, args_json: str):
    mock_tool_call = MagicMock()
    mock_tool_call.id = call_id
    mock_tool_call.function.name = name
    mock_tool_call.function.arguments = args_json
    return mock_tool_call


def _make_tool_call_response(call_id: str, name: str, args_json: str):
    tc = _make_mock_tool_call(call_id, name, args_json)
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = None
    resp.choices[0].message.tool_calls = [tc]
    resp.choices[0].message.model_dump.return_value = {
        "role": "assistant",
        "tool_calls": [{"id": call_id, "function": {"name": name, "arguments": args_json}}],
    }
    return resp


def _make_text_response(content: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.tool_calls = None
    resp.choices[0].message.content = content
    return resp


def test_scenario_a_location_aware_general_question(mock_settings, mock_openai):
    """Scenario A: 'What is the temperature in Mumbai?' with active Mumbai context."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    tool_resp = _make_tool_call_response(
        "call_a",
        "get_live_forecast",
        '{"latitude": 19.076, "longitude": 72.877, "variable": "temperature_2m"}',
    )
    final_resp = _make_text_response("Current live blended temperature in Mumbai is 28.5°C.")
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(
            return_value={"consensus": 28.5, "status": "AVAILABLE"}
        )

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="What is the temperature in Mumbai?")],
            context=AgentContext(
                page="dashboard",
                location="Mumbai",
                latitude=19.076,
                longitude=72.877,
                variable="temperature_2m",
            ),
        )
        res = runtime.run(req)

        assert "28.5°C" in res.response
        assert len(res.tool_activity) == 1
        assert res.tool_activity[0]["tool"] == "get_live_forecast"
        assert res.tool_activity[0]["args"]["latitude"] == 19.076


def test_scenario_b_forecast_context_lead_time_weights(mock_settings, mock_openai):
    """Scenario B: 'What are the 72 hour weights?' with Forecast context."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    tool_resp = _make_tool_call_response(
        "call_b",
        "get_decision_trace",
        '{"latitude": 19.076, "longitude": 72.877, "lead_time_hours": 72}',
    )
    final_resp = _make_text_response("At +72h, the weights are ECMWF: 0.55, GFS: 0.45.")
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(
            return_value={"weights": {"ecmwf": 0.55, "gfs": 0.45}, "status": "AVAILABLE"}
        )

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="What are the 72 hour weights?")],
            context=AgentContext(
                page="forecast",
                location="Mumbai",
                latitude=19.076,
                longitude=72.877,
                lead_time_hours=72,
                variable="temperature_2m",
            ),
        )
        res = runtime.run(req)

        assert "0.55" in res.response
        assert len(res.tool_activity) == 1
        assert res.tool_activity[0]["tool"] == "get_decision_trace"
        assert res.tool_activity[0]["args"]["lead_time_hours"] == 72


def test_scenario_c_dashboard_explain_weights(mock_settings, mock_openai):
    """Scenario C: 'Explain these weights' with Dashboard context -> correct trace retrieved."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    tool_resp = _make_tool_call_response(
        "call_c",
        "get_decision_trace",
        '{"trace_id": "trace_dash_777"}',
    )
    final_resp = _make_text_response(
        "Trace trace_dash_777 confirms GFS received 0.60 weight based on recent RMSE."
    )
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(
            return_value={"trace_id": "trace_dash_777", "weights": {"gfs": 0.6}}
        )

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="Explain these weights")],
            context=AgentContext(
                page="dashboard",
                location="Mumbai",
                latitude=19.076,
                longitude=72.877,
                trace_id="trace_dash_777",
            ),
        )
        res = runtime.run(req)

        assert "trace_dash_777" in res.response
        assert len(res.tool_activity) == 1
        assert res.tool_activity[0]["tool"] == "get_decision_trace"
        assert res.tool_activity[0]["args"]["trace_id"] == "trace_dash_777"


def test_scenario_d_replay_explain_weights(mock_settings, mock_openai):
    """Scenario D: 'Explain these weights' with Replay context -> snapshot trace retrieved."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    tool_resp = _make_tool_call_response(
        "call_d",
        "get_decision_trace",
        '{"replay_id": "rep_999", "lead_time_hours": 24}',
    )
    final_resp = _make_text_response(
        "For historical replay snapshot +24h, the decision trace confirms weights were GFS: 0.6."
    )
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(
            return_value={
                "replay_id": "rep_999",
                "lead_time_hours": 24,
                "weights": {"gfs_seamless": 0.6},
            }
        )

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="Explain these weights")],
            context=AgentContext(
                page="replay",
                location="Mumbai",
                latitude=19.076,
                longitude=72.877,
                replay_id="rep_999",
                lead_time_hours=24,
                trace_id="snap_trace_24",
            ),
        )
        res = runtime.run(req)

        assert "historical replay" in res.response
        assert len(res.tool_activity) == 1
        assert res.tool_activity[0]["tool"] == "get_decision_trace"
        assert res.tool_activity[0]["args"]["replay_id"] == "rep_999"


def test_scenario_e_missing_replay_context_safe_clarification(mock_settings, mock_openai):
    """Scenario E: missing replay context -> safe clarification request without guessing."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # Model asks clarification because neither replay_id nor trace_id nor lead_time exists
    clarification = (
        "Please select a historical replay snapshot or lead time so I can retrieve "
        "the matching DecisionTrace."
    )
    mock_client.chat.completions.create.return_value = _make_text_response(clarification)

    runtime = AgentRuntime()
    req = AgentChatRequest(
        messages=[ChatMessage(role="user", content="Explain these weights")],
        context=AgentContext(page="replay"),  # No snapshot or trace
    )
    res = runtime.run(req)

    assert "select a historical replay snapshot" in res.response
    assert len(res.tool_activity) == 0


def test_scenario_f_invalid_trace_id_safe_evidence_unavailable(mock_settings, mock_openai):
    """Scenario F: invalid trace ID -> safe evidence-unavailable response."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    tool_resp = _make_tool_call_response(
        "call_f",
        "get_decision_trace",
        '{"trace_id": "invalid_trace_xyz"}',
    )
    final_resp = _make_text_response(
        "Evidence unavailable: The requested DecisionTrace (invalid_trace_xyz) could not be found."
    )
    mock_client.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(
            return_value={
                "error": "Decision trace not found for invalid_trace_xyz",
                "status": "UNAVAILABLE",
            }
        )

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="Explain these weights")],
            context=AgentContext(trace_id="invalid_trace_xyz"),
        )
        res = runtime.run(req)

        assert "Evidence unavailable" in res.response
        assert len(res.tool_activity) == 1


def test_scenario_g_provider_unavailable():
    """Scenario G: provider unavailable -> explicit unavailable error."""
    with patch("forecast_forge.agent.providers.nemotron.get_settings") as mock_set:
        settings = MagicMock()
        settings.nvidia_api_key = None
        mock_set.return_value = settings

        runtime = AgentRuntime()
        assert runtime.provider is None

        with pytest.raises(ValueError, match="Nemotron provider unavailable"):
            runtime.run(AgentChatRequest(messages=[ChatMessage(role="user", content="Hi")]))


def test_scenario_h_tool_loop_limit_bounded_failure(mock_settings, mock_openai):
    """Scenario H: tool-loop limit reached -> safe bounded failure."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # Repeated identical tool call returns
    tool_resp = _make_tool_call_response(
        "call_h",
        "get_decision_trace",
        '{"trace_id": "loop_trace"}',
    )
    mock_client.chat.completions.create.return_value = tool_resp

    with patch("forecast_forge.agent.runtime.TOOLS_REGISTRY") as mock_reg:
        mock_reg.__contains__.return_value = True
        mock_reg.__getitem__.return_value = MagicMock(return_value={"trace_id": "loop_trace"})

        runtime = AgentRuntime()
        req = AgentChatRequest(
            messages=[ChatMessage(role="user", content="Explain weights")],
            context=AgentContext(trace_id="loop_trace"),
        )
        res = runtime.run(req)

        # Must exit safely and return bounded limit message
        assert "allowed operational reasoning bounds" in res.response

