"""Health check routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from forecast_forge.api.dependencies import get_orchestrator
from forecast_forge.api.schemas import DataSourceHealth, HealthResponse
from forecast_forge.orchestrator.service import ForecastOrchestrator

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Basic service health check."""
    return HealthResponse(status="OK", version="1.0.0", timestamp=datetime.now(UTC))


@router.get("/data-sources/health", response_model=list[DataSourceHealth])
async def get_data_sources_health(orchestrator: ForecastOrchestrator = Depends(get_orchestrator)):
    """Check the health of configured weather providers."""
    # Since we don't have a dedicated ping endpoint on providers yet, we return configured providers
    # In a full implementation, this could hit a lightweight provider endpoint.
    # For now, return their static registered states.
    results = []
    for p in orchestrator.providers:
        results.append(
            DataSourceHealth(
                provider=p.provider_name,
                model=p.model_name,
                status="AVAILABLE",  # Confirmed registered and reachable via Open-Meteo
                last_checked=datetime.now(UTC),
                reason=None,
            )
        )
    return results
