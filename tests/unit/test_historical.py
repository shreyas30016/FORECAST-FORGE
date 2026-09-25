"""Tests for historical data extraction and alignment."""

from datetime import UTC, date, datetime

import pandas as pd

from forecast_forge.core.models import HistoricalRequest, Location, WeatherVariable
from forecast_forge.historical.alignment import align_and_calculate_errors


def test_historical_request_validation():
    req = HistoricalRequest(
        location=Location(latitude=10.0, longitude=20.0),
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 2),
    )
    assert req.start_date.year == 2023
    assert len(req.variables) == 5
    assert WeatherVariable.TEMPERATURE_2M in req.variables


def test_align_and_calculate_errors():
    models_df = pd.DataFrame(
        [
            {
                "model": "ecmwf_ifs025",
                "valid_time": datetime(2023, 1, 1, 12, tzinfo=UTC),
                "latitude": 10.0,
                "longitude": 20.0,
                "temperature_2m": 25.0,
                "relative_humidity_2m": 80.0,
                "precipitation": 0.0,
                "wind_speed_10m": 10.0,
            }
        ]
    )

    ref_df = pd.DataFrame(
        [
            {
                "model": "era5",
                "valid_time": datetime(2023, 1, 1, 12, tzinfo=UTC),
                "latitude": 10.0,
                "longitude": 20.0,
                "ref_temperature_2m": 24.0,
                "ref_relative_humidity_2m": 85.0,
                "ref_precipitation": 1.0,
                "ref_wind_speed_10m": 12.0,
            }
        ]
    )

    aligned = align_and_calculate_errors(models_df, ref_df)

    assert len(aligned) == 1
    assert aligned.iloc[0]["err_temperature_2m"] == 1.0  # 25 - 24
    assert aligned.iloc[0]["err_precipitation"] == -1.0  # 0 - 1
