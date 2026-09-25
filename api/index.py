"""Vercel serverless entry point for Forecast Forge API."""

from mangum import Mangum
from forecast_forge.api.app import app

# Mangum wraps FastAPI for AWS Lambda/Vercel serverless compatibility
handler = Mangum(app, lifespan="off")
