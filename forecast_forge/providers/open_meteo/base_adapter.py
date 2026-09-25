"""Base Open-Meteo adapter with shared response parsing and validation."""

from datetime import UTC, datetime
from typing import Any

from forecast_forge.config import Settings, get_settings
from forecast_forge.core.enums import ProviderStatus, WeatherVariable
from forecast_forge.core.exceptions import (
    ProviderError,
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from forecast_forge.core.models import (
    ForecastPoint,
    ForecastRequest,
    HistoricalRequest,
    Location,
    ProviderResult,
)
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.base import BaseWeatherProvider
from forecast_forge.providers.http_client import ResilientHTTPClient
from forecast_forge.validation.validator import ForecastValidator

logger = get_logger(__name__)


class OpenMeteoBaseAdapter(BaseWeatherProvider):
    """Base class for Open-Meteo numerical weather prediction model adapters."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: ResilientHTTPClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client or ResilientHTTPClient(self.settings)

    @property
    def provider_name(self) -> str:
        return "Open-Meteo"

    def _build_request_params(self, request: ForecastRequest) -> dict[str, Any]:
        """Construct query parameters for the Open-Meteo forecast API."""
        variable_names = [v.value for v in request.variables]
        return {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
            "hourly": ",".join(variable_names),
            "forecast_days": request.forecast_days,
            "models": self.model_name,
            "timezone": "UTC",
        }

    async def fetch_forecast(self, request: ForecastRequest) -> ProviderResult:
        """Fetch and normalize weather forecast for the specified request."""
        request_timestamp = datetime.now(UTC)
        endpoint = f"{self.settings.open_meteo_base_url}/forecast"
        params = self._build_request_params(request)

        try:
            status_code, data, latency_ms = await self.http_client.get_json(
                url=endpoint,
                params=params,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

            result = self._parse_response(
                data=data,
                request=request,
                status_code=status_code,
                request_timestamp=request_timestamp,
                latency_ms=latency_ms,
            )

        except ProviderRateLimitError as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.RATE_LIMITED,
                request_timestamp=request_timestamp,
                response_status_code=429,
                error_message=str(e),
            )
        except ProviderHTTPError as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.ERROR,
                request_timestamp=request_timestamp,
                response_status_code=e.status_code,
                error_message=str(e),
            )
        except ProviderTimeoutError as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.UNAVAILABLE,
                request_timestamp=request_timestamp,
                error_message=str(e),
            )
        except (ProviderError, Exception) as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.ERROR,
                request_timestamp=request_timestamp,
                error_message=str(e),
            )

        # Mandatory structured log
        self._log_result(result)
        return result

    async def fetch_historical(self, request: HistoricalRequest) -> ProviderResult:
        """Fetch and normalize historical weather forecast for the specified request.

        Supports two verified provider paths:
        1. Single Runs API (Secondary / exact run replay):
           Triggered when request.run is specified. Queries:
           https://single-runs-api.open-meteo.com/v1/forecast?run=YYYY-MM-DDTHH:MM
           Extracts exact initialization_time and computes exact lead_time_hours = valid_time - run.

        2. Previous Runs API (Primary / fixed-lead skill analysis):
           Triggered when request.run is None. Queries:
           https://previous-runs-api.open-meteo.com/v1/forecast
           with variables _previous_day1 to _previous_day7.
           Provides source-defined fixed lead times (24h, 48h, ..., 168h) with
           initialization_time=None (strict anti-fabrication).
        """
        request_timestamp = datetime.now(UTC)

        if request.run is not None:
            endpoint = "https://single-runs-api.open-meteo.com/v1/forecast"
            init_dt = (
                request.run.replace(tzinfo=UTC)
                if request.run.tzinfo is None
                else request.run.astimezone(UTC)
            )
            variable_names = [v.value for v in request.variables]
            params = {
                "latitude": request.location.latitude,
                "longitude": request.location.longitude,
                "hourly": ",".join(variable_names),
                "models": self.model_name,
                "run": init_dt.strftime("%Y-%m-%dT%H:%M"),
                "timezone": "UTC",
            }
            parse_fn = self._parse_single_run_response
        else:
            endpoint = "https://previous-runs-api.open-meteo.com/v1/forecast"
            days = request.lead_time_days or [1, 2, 3, 4, 5, 6, 7]
            hourly_vars: list[str] = []
            for v in request.variables:
                for d in days:
                    hourly_vars.append(f"{v.value}_previous_day{d}")
            params = {
                "latitude": request.location.latitude,
                "longitude": request.location.longitude,
                "models": self.model_name,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "hourly": ",".join(hourly_vars),
                "timezone": "UTC",
            }
            parse_fn = self._parse_previous_runs_response

        try:
            status_code, data, latency_ms = await self.http_client.get_json(
                url=endpoint,
                params=params,
                provider_name=self.provider_name,
                model_name=self.model_name,
            )

            result = parse_fn(
                data=data,
                request=request,
                status_code=status_code,
                request_timestamp=request_timestamp,
                latency_ms=latency_ms,
            )

        except ProviderRateLimitError as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.RATE_LIMITED,
                request_timestamp=request_timestamp,
                response_status_code=429,
                error_message=str(e),
            )
        except ProviderHTTPError as e:
            # 400 errors (e.g. requested run or model unavailable in archive) map to UNAVAILABLE
            status = ProviderStatus.UNAVAILABLE if e.status_code == 400 else ProviderStatus.ERROR
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=status,
                request_timestamp=request_timestamp,
                response_status_code=e.status_code,
                error_message=str(e),
            )
        except ProviderTimeoutError as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.UNAVAILABLE,
                request_timestamp=request_timestamp,
                error_message=str(e),
            )
        except (ProviderError, Exception) as e:
            result = ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ProviderStatus.ERROR,
                request_timestamp=request_timestamp,
                error_message=str(e),
            )

        self._log_result(result)
        return result

    def _parse_single_run_response(
        self,
        data: dict[str, Any],
        request: HistoricalRequest,
        status_code: int,
        request_timestamp: datetime,
        latency_ms: float,
    ) -> ProviderResult:
        """Parse raw Single Runs Open-Meteo response into run-aware ForecastPoints."""
        if "error" in data or "hourly" not in data:
            reason = data.get("reason", "Missing hourly data block")
            status = (
                ProviderStatus.UNAVAILABLE if status_code == 400 else ProviderStatus.NO_VALID_DATA
            )
            return ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=status,
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
                model_name=self.model_name,
                status=ProviderStatus.UNAVAILABLE,
                request_timestamp=request_timestamp,
                response_status_code=status_code,
                latency_ms=latency_ms,
                error_message="Empty time array returned by provider",
            )

        raw_units = data.get("hourly_units", {})
        temp_series = hourly.get(WeatherVariable.TEMPERATURE_2M.value, [])
        hum_series = hourly.get(WeatherVariable.RELATIVE_HUMIDITY_2M.value, [])
        precip_series = hourly.get(WeatherVariable.PRECIPITATION.value, [])
        wind_series = hourly.get(WeatherVariable.WIND_SPEED_10M.value, [])
        cloud_series = hourly.get(WeatherVariable.CLOUD_COVER.value, [])

        records: list[ForecastPoint] = []
        retrieval_dt = datetime.now(UTC)
        assert request.run is not None
        init_dt = (
            request.run.replace(tzinfo=UTC)
            if request.run.tzinfo is None
            else request.run.astimezone(UTC)
        )

        for i, time_str in enumerate(time_series):
            point_dt = datetime.fromisoformat(time_str).replace(tzinfo=UTC)

            # Enforce temporal integrity / causality
            if point_dt < init_dt:
                continue

            lead_hours = (point_dt - init_dt).total_seconds() / 3600.0

            temp = temp_series[i] if i < len(temp_series) else None
            hum = hum_series[i] if i < len(hum_series) else None
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
                model=self.model_name,
                units=raw_units,
                initialization_time=init_dt,
                lead_time_hours=lead_hours,
                lead_time_semantics="EXACT_RUN_CYCLE",
                provenance_source="open_meteo_single_runs",
                retrieval_time=retrieval_dt,
            )
            records.append(point)

        status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
            records=records,
            requested_variables=request.variables,
        )

        return ProviderResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
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

    def _parse_previous_runs_response(
        self,
        data: dict[str, Any],
        request: HistoricalRequest,
        status_code: int,
        request_timestamp: datetime,
        latency_ms: float,
    ) -> ProviderResult:
        """Parse raw Previous Runs Open-Meteo response into fixed lead-time ForecastPoints."""
        if "error" in data or "hourly" not in data:
            reason = data.get("reason", "Missing hourly data block")
            status = (
                ProviderStatus.UNAVAILABLE if status_code == 400 else ProviderStatus.NO_VALID_DATA
            )
            return ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=status,
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
                model_name=self.model_name,
                status=ProviderStatus.UNAVAILABLE,
                request_timestamp=request_timestamp,
                response_status_code=status_code,
                latency_ms=latency_ms,
                error_message="Empty time array returned by provider",
            )

        raw_units = data.get("hourly_units", {})
        records: list[ForecastPoint] = []
        retrieval_dt = datetime.now(UTC)

        days = request.lead_time_days or [1, 2, 3, 4, 5, 6, 7]

        for day in days:
            lead_hours = float(day * 24)
            temp_key = f"{WeatherVariable.TEMPERATURE_2M.value}_previous_day{day}"
            hum_key = f"{WeatherVariable.RELATIVE_HUMIDITY_2M.value}_previous_day{day}"
            precip_key = f"{WeatherVariable.PRECIPITATION.value}_previous_day{day}"
            wind_key = f"{WeatherVariable.WIND_SPEED_10M.value}_previous_day{day}"
            cloud_key = f"{WeatherVariable.CLOUD_COVER.value}_previous_day{day}"

            temp_series = hourly.get(temp_key, [])
            hum_series = hourly.get(hum_key, [])
            precip_series = hourly.get(precip_key, [])
            wind_series = hourly.get(wind_key, [])
            cloud_series = hourly.get(cloud_key, [])

            for i, time_str in enumerate(time_series):
                point_dt = datetime.fromisoformat(time_str).replace(tzinfo=UTC)
                temp = temp_series[i] if i < len(temp_series) else None
                hum = hum_series[i] if i < len(hum_series) else None
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
                    model=self.model_name,
                    units=raw_units,
                    initialization_time=None,  # Anti-fabrication: fixed lead offsets
                    lead_time_hours=lead_hours,
                    lead_time_semantics="FIXED_LEAD_OFFSET",
                    provenance_source=f"open_meteo_previous_runs_day{day}",
                    retrieval_time=retrieval_dt,
                )
                records.append(point)

        status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
            records=records,
            requested_variables=request.variables,
        )

        return ProviderResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
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

    def _parse_response(
        self,
        data: dict[str, Any],
        request: ForecastRequest | HistoricalRequest,
        status_code: int,
        request_timestamp: datetime,
        latency_ms: float,
    ) -> ProviderResult:
        """Parse raw Open-Meteo JSON dictionary into canonical ForecastPoints."""
        if "error" in data or "hourly" not in data:
            reason = data.get("reason", "Missing hourly data block")
            return ProviderResult(
                provider_name=self.provider_name,
                model_name=self.model_name,
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
                model_name=self.model_name,
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

        for i, time_str in enumerate(time_series):
            # Parse timestamp to UTC datetime
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
                model=self.model_name,
                units=raw_units,
                retrieval_time=retrieval_dt,
            )

            if isinstance(request, HistoricalRequest) and getattr(request, "run", None):
                # Phase 5E.1R: We requested a specific run.
                # However, since Open-Meteo's JSON response does not contain an explicit
                # initialization_time field, and we are strictly forbidden from
                # fabricating timestamps, we leave initialization_time and lead_time_hours as None.
                pass

            records.append(point)

        status, valid_count, missing_count = ForecastValidator.assess_dataset_status(
            records=records,
            requested_variables=request.variables,
        )

        return ProviderResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
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

    def _log_result(self, result: ProviderResult) -> None:
        """Output structured log containing all mandatory audit attributes."""
        logger.info(
            "Provider Audit | provider=%s model=%s request_timestamp=%s "
            "response_status=%s record_count=%d valid_record_count=%d "
            "missing_variable_count=%d latency=%.2fms availability_status=%s%s",
            result.provider_name,
            result.model_name,
            result.request_timestamp.isoformat(),
            result.response_status_code or "N/A",
            result.total_records,
            result.valid_records,
            result.missing_variables_count,
            result.latency_ms,
            result.status.value,
            f" error={result.error_message}" if result.error_message else "",
        )

    async def health_check(self) -> ProviderStatus:
        """Lightweight health check against default test coordinates (Mumbai)."""
        test_request = ForecastRequest(
            location=Location(latitude=19.076, longitude=72.8777, name="Mumbai"),
            variables=[WeatherVariable.TEMPERATURE_2M],
            forecast_days=1,
        )
        result = await self.fetch_forecast(test_request)
        return result.status
