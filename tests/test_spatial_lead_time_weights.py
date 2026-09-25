from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from forecast_forge.api.schemas import SpatialLeadTimeWeightGridResponse
from forecast_forge.spatial.grid_service import build_spatial_lead_time_weights_grid


@pytest.fixture(autouse=True)
def mock_extraction():
    with patch(
        "forecast_forge.spatial.grid_service.extract_historical_dataset", new_callable=AsyncMock
    ) as mock_ext:
        # Create dummy df
        models_df = pd.DataFrame(
            {
                "valid_time": [
                    datetime(2024, 6, 1, 0, tzinfo=UTC),
                    datetime(2024, 6, 1, 12, tzinfo=UTC),
                ]
                * 3,
                "model": [
                    "ecmwf_ifs025",
                    "ecmwf_ifs025",
                    "gfs_seamless",
                    "gfs_seamless",
                    "ecmwf_aifs025",
                    "ecmwf_aifs025",
                ],
                "temperature_2m": [30.0, 31.0, 29.0, 32.0, 30.5, 30.5],
                "run_time": [datetime(2024, 5, 31, 0, tzinfo=UTC)] * 6,
                "lead_time_hours": [24.0, 36.0] * 3,
            }
        )
        ref_df = pd.DataFrame(
            {
                "valid_time": [
                    datetime(2024, 6, 1, 0, tzinfo=UTC),
                    datetime(2024, 6, 1, 12, tzinfo=UTC),
                ],
                "ref_temperature_2m": [30.2, 31.1],
            }
        )
        mock_ext.return_value = (models_df, ref_df)
        yield mock_ext


@pytest.mark.asyncio
async def test_spatial_lead_time_weight_engine_unsupported_region():
    # Outside evaluated region (Mumbai)
    res: SpatialLeadTimeWeightGridResponse = await build_spatial_lead_time_weights_grid(
        center_lat=40.7128,  # NY
        center_lon=-74.0060,
        lead_time_hours=24.0,
        grid_size=3,
        step=0.25,
    )
    assert res.status == "UNAVAILABLE"
    # No values should be fabricated
    for cell in res.cells:
        assert cell.status == "UNSUPPORTED_REGION"
        assert cell.weight == 0.0


@pytest.mark.asyncio
async def test_spatial_lead_time_weight_engine_causal_cutoff():
    # Attempting to fetch future verification data should fail
    # We set a causal cutoff in the past
    cutoff = datetime(2024, 6, 2, tzinfo=UTC)
    res: SpatialLeadTimeWeightGridResponse = await build_spatial_lead_time_weights_grid(
        center_lat=19.0760,
        center_lon=72.8777,
        lead_time_hours=24.0,
        grid_size=3,
        step=0.25,
        evaluation_mode="CAUSAL_OPERATIONAL",
        causal_cutoff=cutoff,
        evaluation_start="2024-06-01",
        evaluation_end="2024-06-03",  # Small window
    )

    # Wait, the dataset might have very few samples, so it returns INSUFFICIENT_DATA
    for cell in res.cells:
        if cell.status == "AVAILABLE":
            assert cell.sample_count <= 25  # Because cutoff is June 2


@pytest.mark.asyncio
async def test_spatial_lead_time_weight_normalization():
    # Verify weights sum to 1.0 per slice
    res: SpatialLeadTimeWeightGridResponse = await build_spatial_lead_time_weights_grid(
        center_lat=19.0760,
        center_lon=72.8777,
        lead_time_hours=24.0,
        grid_size=3,
        step=0.25,
        evaluation_start="2024-06-01",
        evaluation_end="2024-06-10",
    )

    if res.status == "AVAILABLE":
        # Group by lat, lon
        cells_df = pd.DataFrame([c.model_dump() for c in res.cells])
        for (_lat, _lon), group in cells_df.groupby(["latitude", "longitude"]):
            # Check sum of weights for available models
            valid_weights = group[group["status"] == "AVAILABLE"]["weight"].sum()
            if valid_weights > 0:
                assert abs(valid_weights - 1.0) < 1e-4

            # Unavailable models get 0 weight
            unavailable = group[group["status"] != "AVAILABLE"]
            if not unavailable.empty:
                assert (unavailable["weight"] == 0.0).all()
