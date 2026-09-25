"""Open-Meteo Ensemble API provider adapter."""

from datetime import UTC, datetime
from typing import Any

import numpy as np

from forecast_forge.config import Settings, get_settings
from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.exceptions import (
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from forecast_forge.core.models import ForecastRequest, ProviderResult
from forecast_forge.ensemble.schemas import (
    EventProbabilityRequest,
    EventProbabilityResult,
    ProbabilisticForecast,
)
from forecast_forge.logging_config import get_logger
from forecast_forge.providers.base import BaseWeatherProvider
from forecast_forge.providers.http_client import ResilientHTTPClient

logger = get_logger(__name__)


class OpenMeteoEnsembleAdapter(BaseWeatherProvider):
    """Adapter for Open-Meteo Ensemble API."""

    def __init__(
        self,
        model_name: str,
        member_prefix: str,
        settings: Settings | None = None,
        http_client: ResilientHTTPClient | None = None,
    ) -> None:
        """
        Initialize the ensemble adapter.

        Args:
            model_name: Open-Meteo ensemble model name (e.g. gfs_seamless, icon_seamless)
            member_prefix: Prefix used for member keys (e.g. ncep_gefs_seamless, icon_seamless_eps)
        """
        self.settings = settings or get_settings()
        self.http_client = http_client or ResilientHTTPClient(self.settings)
        self._model_name = model_name
        self.member_prefix = member_prefix

    @property
    def provider_name(self) -> str:
        return "Open-Meteo Ensemble"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _build_request_params(self, request: ForecastRequest) -> dict[str, Any]:
        """Construct query parameters for the ensemble API."""
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
        """Fetch raw data. For ensembles we return parsed probabilistic models directly."""
        raise NotImplementedError("Use fetch_probabilistic_forecast directly.")

    async def fetch_historical(self, request) -> ProviderResult:
        raise NotImplementedError("Ensemble adapter does not support historical requests.")

    async def health_check(self) -> dict[str, Any]:
        """Check if the ensemble API is reachable."""
        try:
            status_code, _, latency_ms = await self.http_client.get_json(
                url=f"{self.settings.open_meteo_ensemble_url}/ensemble",
                params={
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "hourly": "temperature_2m",
                    "models": self.model_name,
                },
                provider_name=self.provider_name,
                model_name=self.model_name,
            )
            return {
                "status": "up" if status_code == 200 else "down",
                "latency_ms": latency_ms,
                "status_code": status_code,
            }
        except Exception as e:
            return {"status": "down", "error": str(e)}

    async def fetch_probabilistic_forecast(
        self,
        request: ForecastRequest,
        event_requests: list[EventProbabilityRequest] | None = None,
    ) -> dict[WeatherVariable, list[tuple[ProbabilisticForecast, list[EventProbabilityResult]]]]:
        """
        Fetch ensemble members and calculate probabilistic distributions and event probabilities.
        Returns a dict mapping variables to a list of hourly tuples.
        """
        endpoint = f"{self.settings.open_meteo_ensemble_url}/ensemble"

        try:
            status_code, data, latency_ms = await self.http_client.get_json(
                url=endpoint,
                params=self._build_request_params(request),
                provider_name=self.provider_name,
                model_name=self.model_name,
            )
        except (ProviderHTTPError, ProviderRateLimitError, ProviderTimeoutError) as e:
            logger.error(f"Ensemble API error: {e}")
            return {}

        return self._parse_ensemble_response(data, request, event_requests)

    def _parse_ensemble_response(
        self,
        data: dict[str, Any],
        request: ForecastRequest,
        event_requests: list[EventProbabilityRequest] | None = None,
    ) -> dict[WeatherVariable, list[tuple[ProbabilisticForecast, list[EventProbabilityResult]]]]:

        hourly = data.get("hourly", {})
        if not hourly:
            logger.warning(f"No hourly data in ensemble response for {self.model_name}")
            return {}

        times = hourly.get("time", [])
        if not times:
            return {}

        results: dict[
            WeatherVariable, list[tuple[ProbabilisticForecast, list[EventProbabilityResult]]]
        ] = {}

        for variable in request.variables:
            var_name = variable.value

            # Find all member keys for this variable and model prefix
            # Example key: temperature_2m_member01_ncep_gefs_seamless
            # Example deterministic control key: temperature_2m_ncep_gefs_seamless

            member_keys = []
            for k in hourly.keys():
                # Open-Meteo drops the model suffix when requesting a single model
                if k.startswith(f"{var_name}_member"):
                    member_keys.append(k)
                # Control member
                elif k == f"{var_name}_{self.member_prefix}" or k == var_name:
                    member_keys.append(k)

            member_count = len(member_keys)

            var_results = []

            # Use the first timestamp as the reference for lead time calculation
            first_time = datetime.fromisoformat(times[0]).replace(tzinfo=UTC) if times else None

            for i, t_str in enumerate(times):
                valid_time = datetime.fromisoformat(t_str).replace(tzinfo=UTC)

                # Calculate lead time based on the first timestamp in the forecast array
                lead_time_td = valid_time - first_time if first_time else valid_time - valid_time
                lead_time_hours = int(lead_time_td.total_seconds() / 3600)

                if lead_time_hours < 0:
                    continue

                # Extract valid member values
                member_values = []
                for mk in member_keys:
                    val = hourly[mk][i]
                    if val is not None:
                        member_values.append(val)

                valid_member_count = len(member_values)

                if valid_member_count > 0:
                    arr = np.array(member_values)

                    p10 = float(np.percentile(arr, 10))
                    p25 = float(np.percentile(arr, 25))
                    p50 = float(np.percentile(arr, 50))
                    p75 = float(np.percentile(arr, 75))
                    p90 = float(np.percentile(arr, 90))

                    mean_val = float(np.mean(arr))
                    median_val = p50
                    spread_val = float(np.std(arr))
                    status = "AVAILABLE"
                else:
                    p10 = p25 = p50 = p75 = p90 = None
                    mean_val = median_val = spread_val = None
                    status = "INSUFFICIENT_DATA"

                prob_forecast = ProbabilisticForecast(
                    model=self.model_name,
                    variable=var_name,
                    valid_time=valid_time,
                    latitude=request.location.latitude,
                    longitude=request.location.longitude,
                    lead_time_hours=lead_time_hours,
                    member_count=member_count,
                    valid_member_count=valid_member_count,
                    p10=p10,
                    p25=p25,
                    p50=p50,
                    p75=p75,
                    p90=p90,
                    mean=mean_val,
                    median=median_val,
                    spread=spread_val,
                    status=status,
                    provenance=f"Open-Meteo Ensemble API ({self.model_name})",
                )

                # Calculate event probabilities
                event_results = []
                if event_requests:
                    for ev in event_requests:
                        if ev.variable == var_name:
                            if valid_member_count == 0:
                                prob = None
                            else:
                                if ev.operator == ">":
                                    prob = float(np.sum(arr > ev.threshold) / valid_member_count)
                                elif ev.operator == ">=":
                                    prob = float(np.sum(arr >= ev.threshold) / valid_member_count)
                                elif ev.operator == "<":
                                    prob = float(np.sum(arr < ev.threshold) / valid_member_count)
                                elif ev.operator == "<=":
                                    prob = float(np.sum(arr <= ev.threshold) / valid_member_count)
                                else:
                                    prob = None

                            event_results.append(
                                EventProbabilityResult(
                                    variable=var_name,
                                    operator=ev.operator,
                                    threshold=ev.threshold,
                                    probability=prob,
                                    valid_member_count=valid_member_count,
                                    status="AVAILABLE" if prob is not None else "INSUFFICIENT_DATA",
                                )
                            )

                var_results.append((prob_forecast, event_results))

            results[variable] = var_results

        return results
