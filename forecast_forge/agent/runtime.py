# ruff: noqa: E501
import json

from .prompts import SCIENTIFIC_SYSTEM_PROMPT
from .providers.nemotron import NemotronProvider
from .schemas import AgentChatRequest, AgentChatResponse
from .tools import TOOLS_REGISTRY, TOOLS_SCHEMA


class AgentRuntime:
    def __init__(self):
        try:
            self.provider = NemotronProvider()
        except ValueError as e:
            # During unit testing without keys, we shouldn't fail instantiation
            # Instead, fail on execution
            self.provider = None
            self.init_error = str(e)

    def run(self, request: AgentChatRequest) -> AgentChatResponse:
        if not self.provider:
            raise ValueError(f"Nemotron provider unavailable: {self.init_error}")

        messages = [{"role": "system", "content": SCIENTIFIC_SYSTEM_PROMPT}]

        # Inject context into system prompt silently
        if request.context:
            ctx_dump = request.context.model_dump(exclude_none=True)
            if ctx_dump:
                ctx_str = json.dumps(ctx_dump, indent=2)
                messages[0]["content"] += f"\n\nCURRENT APPLICATION CONTEXT:\n{ctx_str}"
                messages[0]["content"] += (
                    "\n\nCONTEXT RULES & PRECEDENCE:\n"
                    "- If `trace_id` is provided in context, always call `get_decision_trace(trace_id=...)` FIRST to fetch the authoritative record.\n"
                    "- If on Replay with `replay_id` and `lead_time_hours`, call `get_decision_trace(replay_id=..., lead_time_hours=...)`.\n"
                    "- For general weather/forecast questions (e.g. 'What is the temperature in [City]?') when latitude/longitude are present in context, call `get_live_forecast` directly using those coordinates. Do NOT ask the user for coordinates or city name if they already exist in context.\n"
                    "- If DecisionTrace is missing, unavailable, or degraded, state the evidence limitation clearly without estimating or inventing numbers."
                )

        # Append user messages
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        tool_activity = []
        seen_tool_calls: set[tuple[str, str]] = set()
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response_msg = self.provider.generate_chat(messages, tools=TOOLS_SCHEMA)
            except Exception as e:
                return AgentChatResponse(
                    response=f"I couldn't retrieve the required forecast evidence. (Provider error: {str(e)})",
                    tool_activity=tool_activity,
                )

            if response_msg.tool_calls:
                # Add assistant message with tool calls
                messages.append(response_msg.model_dump(exclude_none=True))

                for tool_call in response_msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = tool_call.function.arguments

                    try:
                        args_dict = json.loads(func_args)
                    except json.JSONDecodeError:
                        args_dict = {}

                    tool_activity.append(
                        {"tool": func_name, "args": args_dict, "status": "executing"}
                    )

                    # Guard against runaway identical tool invocations
                    call_key = (func_name, json.dumps(args_dict, sort_keys=True))
                    if call_key in seen_tool_calls:
                        result = {
                            "status": "UNAVAILABLE",
                            "reason": f"Tool '{func_name}' was already executed with identical arguments in this session.",
                        }
                    else:
                        seen_tool_calls.add(call_key)
                        if func_name in TOOLS_REGISTRY:
                            try:
                                result = TOOLS_REGISTRY[func_name](**args_dict)
                            except Exception as e:
                                result = {"status": "ERROR", "reason": str(e)}
                        else:
                            result = {"status": "ERROR", "reason": f"Unknown tool: {func_name}"}

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )
            else:
                return AgentChatResponse(
                    response=response_msg.content or "", tool_activity=tool_activity
                )

        return AgentChatResponse(
            response="I apologize, but I could not complete the requested evidence gathering within the allowed operational reasoning bounds. Please narrow or refine your request.",
            tool_activity=tool_activity,
        )
