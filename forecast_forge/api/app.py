"""FastAPI application factory and configuration."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forecast_forge.api.errors import APIException, api_exception_handler, global_exception_handler
from forecast_forge.api.routes import (
    bust,
    ensemble,
    evaluation,
    extremes,
    forecast,
    health,
    historical,
    models,
    probabilistic,
    replay,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Forecast Forge AI API",
        description="Production API for Forecast Forge ensemble engine.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    # In production (Vercel), frontend and backend share same origin, but CORS still needed for credentials
    # In development, allow localhost origins
    allowed_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://forecast-forge-ai.vercel.app,http://localhost:3000,http://127.0.0.1:3000"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in allowed_origins.split(",")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # Routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(models.router, prefix="/api/v1", tags=["Models"])
    app.include_router(forecast.router, prefix="/api/v1", tags=["Forecast"])
    app.include_router(ensemble.router, prefix="/api/v1", tags=["Ensemble"])
    app.include_router(evaluation.router, prefix="/api/v1", tags=["Evaluation"])
    app.include_router(historical.router, prefix="/api/v1", tags=["Historical"])
    app.include_router(probabilistic.router, prefix="/api/v1", tags=["Probabilistic"])
    app.include_router(extremes.router, prefix="/api/v1", tags=["Extremes"])
    app.include_router(bust.router, prefix="/api/v1", tags=["Bust"])
    app.include_router(replay.router, prefix="/api/v1", tags=["Replay"])

    from forecast_forge.api.trace_router import router as trace_router

    app.include_router(trace_router)

    from forecast_forge.api.agent_router import router as agent_router

    app.include_router(agent_router)

    return app


app = create_app()
