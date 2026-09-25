"""Historical routes."""

from fastapi import APIRouter

from forecast_forge.api.schemas import HistoricalDataAPI, LocationAPI

router = APIRouter()


@router.get("/historical", response_model=HistoricalDataAPI)
async def get_historical():
    """Mock endpoint for historical dataset views (read-only)."""
    return HistoricalDataAPI(
        location=LocationAPI(name="Mumbai", latitude=19.0760, longitude=72.8777),
        variable="temperature_2m",
        data=[],  # Would return aggregated parquet rows
    )
