from typing import Any

from pydantic import BaseModel, Field


class CopilotContext(BaseModel):
    page: str | None = Field(default=None, description="Current page: dashboard, forecast, replay")
    location: str | None = Field(default=None, description="Location name, e.g. Mumbai")
    latitude: float | None = Field(default=None, description="Latitude coordinate")
    longitude: float | None = Field(default=None, description="Longitude coordinate")
    variable: str | None = Field(default="temperature_2m", description="Target variable")
    lead_time_hours: int | None = Field(default=None, description="Lead time in hours")
    valid_time: str | None = Field(default=None, description="Target valid time (ISO string)")
    run_time: str | None = Field(default=None, description="Model run time (ISO string)")
    trace_id: str | None = Field(default=None, description="Canonical DecisionTrace ID")
    replay_id: str | None = Field(default=None, description="Replay session/timeline ID")
    replay_status: str | None = Field(default=None, description="Replay status: EXACT, DEGRADED")
    provenance_status: str | None = Field(
        default=None, description="Provenance status: AVAILABLE, etc."
    )
    selected_model: str | None = Field(default=None, description="Selected model")
    forecast_value: float | None = Field(default=None, description="Forecast value")
    realized_value: float | None = Field(default=None, description="Realized verification value")
    active_overlay: str | None = Field(default=None, description="Active GIS overlay")


# Backward compatibility alias
AgentContext = CopilotContext


class ChatMessage(BaseModel):
    role: str = Field(description="Role of the sender (user, assistant, system)")
    content: str = Field(description="Content of the message")


class AgentChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: CopilotContext | None = None


class AgentChatResponse(BaseModel):
    response: str
    tool_activity: list[dict[str, Any]] = Field(default_factory=list)
