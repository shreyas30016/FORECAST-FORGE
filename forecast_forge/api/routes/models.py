"""Model information routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from forecast_forge.api.dependencies import get_orchestrator
from forecast_forge.api.schemas import ModelInfo
from forecast_forge.orchestrator.service import ForecastOrchestrator

router = APIRouter()


@router.get("/models", response_model=list[ModelInfo])
async def list_models(orchestrator: ForecastOrchestrator = Depends(get_orchestrator)):
    """List available numerical weather prediction models and capabilities."""
    results = []
    for p in orchestrator.providers:
        results.append(
            ModelInfo(
                name=p.model_name,
                provider=p.provider_name,
                status="AVAILABLE",  # Default assumption before query
                capabilities=["hourly"],
                last_checked=datetime.now(UTC),
                available_variables=[
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                ],
                supported_forecast_horizon_hours=72,
                reason=None,
            )
        )
    return results
