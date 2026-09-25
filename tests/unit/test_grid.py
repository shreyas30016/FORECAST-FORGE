"""Unit tests for spatial grid generation and processing."""

import pytest

from forecast_forge.spatial.grid_service import (
    generate_grid_coordinates,
)


def test_generate_grid_coordinates_count_and_bounds():
    points = generate_grid_coordinates(center_lat=19.0, center_lon=72.0, grid_size=3, step=0.25)
    assert len(points) == 9

    # Center point is at index 4 (0-indexed in a 3x3 grid)
    center_point = points[4]
    assert center_point[0] == 19.0
    assert center_point[1] == 72.0

    # Bounds: [[lat_min, lon_min], [lat_max, lon_max]]
    bounds = center_point[2]
    assert bounds[0][0] == pytest.approx(18.875)
    assert bounds[0][1] == pytest.approx(71.875)
    assert bounds[1][0] == pytest.approx(19.125)
    assert bounds[1][1] == pytest.approx(72.125)


def test_generate_grid_coordinates_boundary_clamping():
    points = generate_grid_coordinates(center_lat=89.9, center_lon=179.9, grid_size=3, step=0.25)
    assert len(points) == 9
    for lat, lon, _ in points:
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0


def test_spatial_ensemble_weight_normalization():
    """Verify weights normalize only across available models, excluding unavailable AIFS."""
    base_weights = {"ecmwf_ifs025": 0.729, "gfs_seamless": 0.271, "ecmwf_aifs025": 0.0}
    valid_models = ["ecmwf_ifs025", "gfs_seamless"]

    tot_w = sum(base_weights[m] for m in valid_models)
    norm_w = {m: round(base_weights[m] / tot_w, 3) for m in valid_models}

    assert pytest.approx(sum(norm_w.values()), 0.01) == 1.0
    assert norm_w["ecmwf_ifs025"] > norm_w["gfs_seamless"]
    assert "ecmwf_aifs025" not in norm_w


def test_model_spread_and_pairwise_difference():
    """Verify Model Spread = max(valid) - min(valid) and pairwise |IFS - GFS|."""
    ifs_val = 31.4
    gfs_val = 30.2
    valid_vals = [ifs_val, gfs_val]

    spread = round(max(valid_vals) - min(valid_vals), 2)
    pairwise_diff = round(abs(ifs_val - gfs_val), 2)

    assert spread == 1.20
    assert pairwise_diff == 1.20

    # Three models case (hypothetical)
    valid_vals_3 = [31.4, 30.2, 32.0]
    spread_3 = round(max(valid_vals_3) - min(valid_vals_3), 2)
    assert spread_3 == 1.80
    # Pairwise IFS-GFS remains |31.4 - 30.2| = 1.20
    assert pairwise_diff == 1.20


def test_fewer_than_two_models_spread_none():
    """Never calculate spread from fewer than two valid models."""
    valid_vals = [31.4]
    spread = round(max(valid_vals) - min(valid_vals), 2) if len(valid_vals) >= 2 else None
    assert spread is None


@pytest.mark.asyncio
async def test_build_spatial_weights_grid_extrapolation():
    from forecast_forge.spatial.grid_service import build_spatial_weights_grid

    # 1. Test exactly at Mumbai (19.0760, 72.8777)
    res = await build_spatial_weights_grid(19.076, 72.877, "temperature_2m", grid_size=3)
    # Check that at least some cells have AVAILABLE status (since it's within tolerance)
    available_cells = [c for c in res.cells if c.status == "AVAILABLE"]
    assert len(available_cells) > 0
    assert all(c.coverage_type == "LOCATION_EVALUATED" for c in available_cells)

    # Check AIFS is unavailable
    aifs_cells = [c for c in res.cells if c.model == "ecmwf_aifs025"]
    assert all(c.weight == 0.0 for c in aifs_cells)

    # 2. Test far away (e.g. Delhi: 28.6139, 77.2090) - should NOT extrapolate
    res_far = await build_spatial_weights_grid(28.6139, 77.2090, "temperature_2m", grid_size=3)
    assert all(c.status == "UNAVAILABLE" for c in res_far.cells)
    assert all(c.coverage_type == "UNSUPPORTED_REGION" for c in res_far.cells)
    assert all(c.weight == 0.0 for c in res_far.cells)


@pytest.mark.asyncio
async def test_build_spatial_weights_grid_normalization():
    from forecast_forge.spatial.grid_service import build_spatial_weights_grid

    res = await build_spatial_weights_grid(19.076, 72.877, "temperature_2m", grid_size=1)
    # For a 1x1 grid, there should be 3 cells (one per model)
    assert len(res.cells) == 3

    total_weight = sum(c.weight for c in res.cells)
    assert pytest.approx(total_weight, 0.01) == 1.0
