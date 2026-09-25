"""Retrieval of ERA5 reanalysis as a reference/observational dataset."""

from datetime import UTC, datetime
from typing import Any

from forecast_forge.config import get_settings
from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.models import ForecastPoint, HistoricalRequest, ProviderResult
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.http_client import ResilientHTTPClient

logger = get_logger(__name__)


class ERA5ReferenceProvider:
    """Adapter for retrieving historical ERA5 reanalysis data as a reference benchmark dataset.

    Note: Reanalysis combines model-data assimilation, not in-situ station observations.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.http_client = ResilientHTTPClient(self.settings)

    @property
    def provider_name(self) -> str:
        return "ERA5_Reanalysis"

    async def fetch_reference_data(self, request: HistoricalRequest) -> ProviderResult:
        """Fetch historical ERA5 data for the specified dates and location."""
        request_timestamp = datetime.now(UTC)
        # ERA5 is available via the archive API endpoint
        endpoint = f"{self.settings.open_meteo_archive_url}/archive"

        variable_names = [v.value for v in request.variables]
        params = {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
            "hourly": ",".join(variable_names),
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "timezone": "UTC",
        }

        logger.info(
            "Fetching ERA5 reference data for %s to %s", request.start_date, request.end_date
        )

        try:
            status_code, data, latency_ms = await self.http_client.get_json(
                url=endpoint,
                params=params,
                provider_name=self.provider_name,
                model_name="era5",
            )
            return self._parse_response(
                data=data,
                request=request,
                status_code=status_code,
                request_timestamp=request_timestamp,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error("Failed to fetch ERA5 data: %s", e)
            return ProviderResult(
                provider_name=self.provider_name,
                model_name="era5",
                status=ProviderStatus.ERROR,
                request_timestamp=request_timestamp,
                error_message=str(e),
            )

    def _parse_response(
        self,
        data: dict[str, Any],
        request: HistoricalRequest,
        status_code: int,
        request_timestamp: datetime,
        latency_ms: float,
    ) -> ProviderResult:
        """Parse raw Open-Meteo ERA5 JSON dictionary into canonical ForecastPoints."""
        if "error" in data or "hourly" not in data:
            reason = data.get("reason", "Missing hourly data block")
            return ProviderResult(
                provider_name=self.provider_name,
                model_name="era5",
                status=ProviderStatus.NO_VALID_DATA,
                request_timestamp=request_timestamp,
                response_status_code=status_code,
                latency_ms=latency_ms,
                error_message=f"Provider response error: {reason}",
            )

        hourly = data["hourly"]
        time_series: list[str] = hourly.get("time", [])
        if not time_series:
            return ProviderResult(
                provider_name=self.provider_name,
                model_name="era5",
                status=ProviderStatus.UNAVAILABLE,
                request_timestamp=request_timestamp,
                response_status_code=status_code,
                latency_ms=latency_ms,
                error_message="Empty time array returned by provider",
            )

        raw_units = data.get("hourly_units", {})
        temp_series = hourly.get(WeatherVariable.TEMPERATURE_2M.value, [])
        humidity_series = hourly.get(WeatherVariable.RELATIVE_HUMIDITY_2M.value, [])
        precip_series = hourly.get(WeatherVariable.PRECIPITATION.value, [])
        wind_series = hourly.get(WeatherVariable.WIND_SPEED_10M.value, [])
        cloud_series = hourly.get(WeatherVariable.CLOUD_COVER.value, [])

        records: list[ForecastPoint] = []
        retrieval_dt = datetime.now(UTC)

        valid_count = 0
        missing_count = 0

        for i, time_str in enumerate(time_series):
            point_dt = datetime.fromisoformat(time_str).replace(tzinfo=UTC)

            temp = temp_series[i] if i < len(temp_series) else None
            hum = humidity_series[i] if i < len(humidity_series) else None
            precip = precip_series[i] if i < len(precip_series) else None
            wind = wind_series[i] if i < len(wind_series) else None
            cloud = cloud_series[i] if i < len(cloud_series) else None

            point = ForecastPoint(
                timestamp=point_dt,
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                temperature_2m=temp,
                precipitation=precip,
                wind_speed_10m=wind,
                relative_humidity_2m=hum,
                cloud_cover=cloud,
                provider=self.provider_name,
                model="era5",
                units=raw_units,
                retrieval_time=retrieval_dt,
            )
            records.append(point)

            req_vals = [getattr(point, v.value, None) for v in request.variables]
            if req_vals and all(v is not None for v in req_vals):
                valid_count += 1
            else:
                missing_count += 1

        status = ProviderStatus.AVAILABLE if valid_count > 0 else ProviderStatus.UNAVAILABLE

        return ProviderResult(
            provider_name=self.provider_name,
            model_name="era5",
            status=status,
            records=records,
            request_timestamp=request_timestamp,
            response_status_code=status_code,
            total_records=len(records),
            valid_records=valid_count,
            missing_variables_count=missing_count,
            latency_ms=latency_ms,
            raw_units=raw_units,
        )
