"""Service for Extreme Weather Guidance."""

from datetime import UTC, datetime
from pathlib import Path

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.ensemble.schemas import EventProbabilityRequest
from forecast_forge.extremes.schemas import (
    EventDefinition,
    EventGuidance,
    RegimeContext,
    SpatialContext,
)
from forecast_forge.providers.open_meteo.ensemble import OpenMeteoEnsembleAdapter

try:
    from forecast_forge.evaluation.regimes.assignment import RegimeAssigner
    from forecast_forge.evaluation.regimes.clustering import RegimeDiscoveryPipeline
except ImportError:
    RegimeDiscoveryPipeline = None
    RegimeAssigner = None

# Initial supported events configuration
DEFAULT_EVENTS = [
    EventDefinition(
        event_type="Heavy Rain", variable="precipitation", operator=">=", threshold=25.0, unit="mm"
    ),
    EventDefinition(
        event_type="Extreme Temperature",
        variable="temperature_2m",
        operator=">=",
        threshold=35.0,
        unit="°C",
    ),
    EventDefinition(
        event_type="High Wind",
        variable="wind_speed_10m",
        operator=">=",
        threshold=50.0,
        unit="km/h",
    ),
]


class ExtremesService:
    """Core logic for extracting empirical extreme weather probabilities."""

    def __init__(self, events: list[EventDefinition] = DEFAULT_EVENTS):
        self.events = events
        self.regime_assigner = None
        self.pipeline = None
        model_path = Path(".model_cache/regimes/mumbai_k3.joblib")
        if model_path.exists() and RegimeDiscoveryPipeline:
            try:
                self.pipeline = RegimeDiscoveryPipeline.load(str(model_path))
                self.regime_assigner = RegimeAssigner(self.pipeline)
            except Exception:
                pass

    async def get_guidance(
        self,
        latitude: float,
        longitude: float,
        location_name: str,
        lead_time_hours: int,
        model: str,
    ) -> list[EventGuidance]:
        """Fetch empirical ensemble probabilities for extreme events."""

        # Determine adapter config
        if model in ["gfs_seamless", "gfs_ensemble"]:
            api_model = "gfs_seamless"
            prefix = "ncep_gefs_seamless"
        elif model in ["icon_seamless", "icon_ensemble"]:
            api_model = "icon_seamless"
            prefix = "icon_seamless_eps"
        elif model in ["ecmwf_ifs04_ensemble", "ecmwf_ensemble", "ecmwf_ifs025", "ecmwf_ifs04"]:
            api_model = "ecmwf_ifs04"
            prefix = "ecmwf_ifs04"
        elif model == "ecmwf_aifs025":
            api_model = "ecmwf_aifs025"
            prefix = "ecmwf_aifs025"
        else:
            api_model = "gfs_seamless"
            prefix = "ncep_gefs_seamless"

        adapter = OpenMeteoEnsembleAdapter(model_name=api_model, member_prefix=prefix)
        loc = Location(name=location_name, latitude=latitude, longitude=longitude)

        # Convert events into probability requests
        variables_to_request = set()
        event_requests = []
        for ev in self.events:
            try:
                var_enum = WeatherVariable(ev.variable)
                variables_to_request.add(var_enum)
                event_requests.append(
                    EventProbabilityRequest(
                        variable=ev.variable, operator=ev.operator, threshold=ev.threshold
                    )
                )
            except ValueError:
                continue

        regime_features = [
            WeatherVariable.TEMPERATURE_2M,
            WeatherVariable.RELATIVE_HUMIDITY_2M,
            WeatherVariable.PRECIPITATION,
            WeatherVariable.WIND_SPEED_10M,
            WeatherVariable.CLOUD_COVER,
        ]
        if self.regime_assigner:
            for rf in regime_features:
                variables_to_request.add(rf)

        req = ForecastRequest(
            location=loc,
            variables=list(variables_to_request),
            forecast_days=(lead_time_hours // 24) + 1,
        )

        guidance_results = []

        try:
            results = await adapter.fetch_probabilistic_forecast(req, event_requests)
        except Exception:
            for ev in self.events:
                guidance_results.append(
                    self._create_error_guidance(
                        ev,
                        latitude,
                        longitude,
                        location_name,
                        lead_time_hours,
                        api_model,
                        "UNAVAILABLE",
                    )
                )
            return guidance_results

        regime_context = None
        if self.regime_assigner:
            forecast_dict = {}
            for rf in regime_features:
                if rf in results and results[rf]:
                    target_time_data = None
                    for prob_fcst, _ in results[rf]:
                        if prob_fcst.lead_time_hours == lead_time_hours:
                            target_time_data = prob_fcst
                            break
                    if target_time_data and target_time_data.mean is not None:
                        forecast_dict[rf.value] = target_time_data.mean
                    else:
                        forecast_dict[rf.value] = None

            assignment = self.regime_assigner.assign_forecast_state(forecast_dict)
            if assignment.is_valid:
                for r in self.pipeline.regimes:
                    if r.regime_id == assignment.regime_id:
                        regime_context = RegimeContext(
                            current_regime=f"Regime {r.regime_id}",
                            regime_id=r.regime_id,
                            regime_description=r.description,
                            regime_sample_count=r.sample_count,
                        )
                        break

        for ev in self.events:
            try:
                var_enum = WeatherVariable(ev.variable)
            except ValueError:
                continue

            if var_enum not in results or not results[var_enum]:
                guidance_results.append(
                    self._create_error_guidance(
                        ev,
                        latitude,
                        longitude,
                        location_name,
                        lead_time_hours,
                        api_model,
                        "UNAVAILABLE",
                    )
                )
                continue

            time_series = results[var_enum]
            target_data = None
            for prob_fcst, event_probs in time_series:
                if prob_fcst.lead_time_hours == lead_time_hours:
                    target_data = (prob_fcst, event_probs)
                    break

            if not target_data:
                guidance_results.append(
                    self._create_error_guidance(
                        ev,
                        latitude,
                        longitude,
                        location_name,
                        lead_time_hours,
                        api_model,
                        "UNAVAILABLE",
                    )
                )
                continue

            prob_fcst, event_probs = target_data

            target_event_prob = None
            for ep in event_probs:
                if (
                    ep.variable == ev.variable
                    and ep.operator == ev.operator
                    and ep.threshold == ev.threshold
                ):
                    target_event_prob = ep
                    break

            if (
                not target_event_prob
                or prob_fcst.status != "AVAILABLE"
                or target_event_prob.status != "AVAILABLE"
            ):
                guidance_results.append(
                    self._create_error_guidance(
                        ev,
                        latitude,
                        longitude,
                        location_name,
                        lead_time_hours,
                        api_model,
                        "INSUFFICIENT_DATA",
                    )
                )
                continue

            guidance = EventGuidance(
                event_type=ev.event_type,
                threshold=ev.threshold,
                probability=target_event_prob.probability,
                probability_method="empirical ensemble-member probability",
                lead_time_hours=lead_time_hours,
                valid_time=prob_fcst.valid_time,
                location=location_name,
                ensemble_member_count=prob_fcst.member_count,
                valid_member_count=prob_fcst.valid_member_count,
                active_models=[api_model],
                regime=regime_context,
                spatial_context=SpatialContext(
                    latitude=latitude,
                    longitude=longitude,
                    is_supported=True,
                ),
                status="AVAILABLE",
                provenance=prob_fcst.provenance,
            )
            guidance_results.append(guidance)

        return guidance_results

    def _create_error_guidance(
        self,
        ev: EventDefinition,
        lat: float,
        lon: float,
        loc_name: str,
        lead: int,
        model: str,
        status: str,
    ) -> EventGuidance:
        return EventGuidance(
            event_type=ev.event_type,
            threshold=ev.threshold,
            probability=None,
            probability_method="empirical ensemble-member probability",
            lead_time_hours=lead,
            valid_time=datetime.now(UTC),
            location=loc_name,
            ensemble_member_count=0,
            valid_member_count=0,
            active_models=[model],
            spatial_context=SpatialContext(
                latitude=lat,
                longitude=lon,
                is_supported=False if status == "UNSUPPORTED_REGION" else True,
            ),
            status=status,
            provenance="unknown",
        )
