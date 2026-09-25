"""Tests for the FastAPI integration layer."""

from fastapi.testclient import TestClient

from forecast_forge.api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "version" in data
    assert "timestamp" in data


def test_data_sources_health():
    response = client.get("/api/v1/data-sources/health")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["provider"] == "Open-Meteo"
    assert data[0]["status"] == "AVAILABLE"


def test_models_endpoint():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [m["name"] for m in data]
    assert "ecmwf_ifs025" in names
    assert "gfs_seamless" in names
    assert "ecmwf_aifs025" in names
    assert "temperature_2m" in data[0]["available_variables"]


def test_forecast_missing_params():
    response = client.get("/api/v1/forecast")
    assert response.status_code == 422  # Validation Error


def test_ensemble_missing_params():
    response = client.get("/api/v1/ensemble")
    assert response.status_code == 422  # Validation Error


def test_evaluation_endpoint():
    response = client.get("/api/v1/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "evaluations" in data
    evaluations = data["evaluations"]
    assert len(evaluations) >= 5
    models = [d["model"] for d in evaluations]
    assert "ecmwf_ifs025" in models
    assert "gfs_seamless" in models
    assert "ecmwf_aifs025" in models
    aifs = next(d for d in evaluations if d["model"] == "ecmwf_aifs025")
    assert aifs["status"] == "UNAVAILABLE"
    assert aifs["sample_count"] == 0


def test_historical_endpoint():
    response = client.get("/api/v1/historical")
    assert response.status_code == 200


def test_forecast_grid_missing_params():
    response = client.get("/api/v1/forecast/grid")
    assert response.status_code == 422


def test_forecast_grid_endpoint():
    response = client.get(
        "/api/v1/forecast/grid?latitude=19.0760&longitude=72.8777&variable=temperature_2m&model=ecmwf_ifs025&grid_size=3"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["points_count"] == 9
    assert data["variable"] == "temperature_2m"
    assert data["unit"] == "°C"
    assert len(data["cells"]) == 9
    assert "bounds" in data["cells"][0]
    assert data["spatial_uncertainty_available"] is False


def test_forecast_grid_ensemble_endpoint():
    response = client.get(
        "/api/v1/forecast/grid?latitude=19.0760&longitude=72.8777&variable=temperature_2m&model=ensemble&grid_size=3"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["points_count"] == 9
    assert data["model"] == "ensemble"
    assert data["ensemble_summary"] is not None
    assert "ensemble_value" in data["ensemble_summary"]
    assert "models" in data["ensemble_summary"]
    assert "ecmwf_ifs025" in data["ensemble_summary"]["models"]
    assert "gfs_seamless" in data["ensemble_summary"]["models"]
    assert data["ensemble_summary"]["models"]["ecmwf_aifs025"]["status"] == "UNAVAILABLE"
    # Check cells have ensemble fields
    first_cell = data["cells"][0]
    assert "ensemble_value" in first_cell
    assert "weights_applied" in first_cell
