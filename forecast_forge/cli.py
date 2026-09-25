"""Command-line interface and smoke testing utility for Forecast Forge AI."""

import argparse
import asyncio
import sys

from forecast_forge.config import get_settings
from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.logging_config import configure_logging, get_logger
from forecast_forge.orchestrator.service import ForecastOrchestrator

logger = get_logger("forecast_forge.cli")


async def run_smoke_test(lat: float, lon: float, location_name: str, days: int) -> int:
    """Execute live provider smoke test and output structured audit results."""
    settings = get_settings()
    configure_logging(settings.log_level)

    print("=" * 80)
    print(" FORECAST FORGE AI -- PROVIDER LAYER SMOKE TEST")
    print("=" * 80)
    print(f"Target Location : {location_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")
    print(f"Forecast Horizon: {days} days")
    print(f"Base Endpoint   : {settings.open_meteo_base_url}")
    print("-" * 80)

    request = ForecastRequest(
        location=Location(latitude=lat, longitude=lon, name=location_name),
        variables=[
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
        ],
        forecast_days=days,
    )

    orchestrator = ForecastOrchestrator(settings=settings)
    results = await orchestrator.fetch_all(request)

    print("\n" + "=" * 80)
    print(" PROVIDER AUDIT SUMMARY")
    print("=" * 80)
    header = (
        f"{'Provider':<12} | {'Model':<16} | {'Status':<14} | "
        f"{'Total':<5} | {'Valid':<5} | {'Missing':<7} | {'Latency':<9}"
    )
    print(header)
    print("-" * len(header))

    for model_name, res in results.items():
        print(
            f"{res.provider_name:<12} | "
            f"{model_name:<16} | "
            f"{res.status.value:<14} | "
            f"{res.total_records:<5} | "
            f"{res.valid_records:<5} | "
            f"{res.missing_variables_count:<7} | "
            f"{res.latency_ms:>6.1f} ms"
        )
        if res.error_message:
            print(f"  -> Detail / Error: {res.error_message}")
        elif res.records and res.valid_records > 0:
            sample = res.records[0]
            print(
                f"  -> Sample ({sample.timestamp.strftime('%Y-%m-%d %H:%M UTC')}): "
                f"T={sample.temperature_2m} C, RH={sample.relative_humidity_2m}%, "
                f"Precip={sample.precipitation} mm, Wind={sample.wind_speed_10m} km/h"
            )

    print("=" * 80)
    print("Smoke test completed.")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Forecast Forge AI — Provider Layer CLI & Smoke Test"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    smoke_parser = subparsers.add_parser(
        "smoke-test", help="Query live weather providers for a location"
    )
    smoke_parser.add_argument(
        "--lat", type=float, default=19.0760, help="Latitude (default: Mumbai)"
    )
    smoke_parser.add_argument(
        "--lon", type=float, default=72.8777, help="Longitude (default: Mumbai)"
    )
    smoke_parser.add_argument("--name", type=str, default="Mumbai", help="Location name")
    smoke_parser.add_argument("--days", type=int, default=2, help="Forecast days")

    args = parser.parse_args()

    # Default to smoke-test if no subcommand is passed
    if args.command is None or args.command == "smoke-test":
        lat = getattr(args, "lat", 19.0760)
        lon = getattr(args, "lon", 72.8777)
        name = getattr(args, "name", "Mumbai")
        days = getattr(args, "days", 2)
        exit_code = asyncio.run(run_smoke_test(lat=lat, lon=lon, location_name=name, days=days))
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
