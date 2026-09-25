from fastapi import APIRouter, HTTPException

from forecast_forge.agent.runtime import AgentRuntime
from forecast_forge.agent.schemas import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

runtime = AgentRuntime()


@router.post("/chat", response_model=AgentChatResponse)
async def chat(request: AgentChatRequest):
    """Chat with the Forecast Copilot."""
    try:
        response = runtime.run(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}") from None
