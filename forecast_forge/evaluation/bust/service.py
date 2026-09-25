"""Service orchestration for Forecast-Bust Intelligence."""

from pathlib import Path

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.evaluation.bust.detector import ForecastBustDetector
from forecast_forge.evaluation.bust.schemas import BustFactor, ForecastBustSignal
from forecast_forge.providers.open_meteo.ensemble import OpenMeteoEnsembleAdapter

try:
    from forecast_forge.evaluation.regimes.assignment import RegimeAssigner
    from forecast_forge.evaluation.regimes.clustering import RegimeDiscoveryPipeline
except ImportError:
    RegimeDiscoveryPipeline = None
    RegimeAssigner = None


class ForecastBustService:
    def __init__(self):
        self.detector = None
        self.regime_assigner = None

        detector_path = Path(".model_cache/bust/mumbai_bust_model.joblib")
        if detector_path.exists():
            try:
                self.detector = ForecastBustDetector.load(str(detector_path))
            except Exception:
                pass

        regime_path = Path(".model_cache/regimes/mumbai_k3.joblib")
        if regime_path.exists() and RegimeDiscoveryPipeline:
            try:
                pipeline = RegimeDiscoveryPipeline.load(str(regime_path))
                self.regime_assigner = RegimeAssigner(pipeline)
            except Exception:
                pass

    async def get_bust_signal(
        self,
        latitude: float,
        longitude: float,
        location_name: str,
        lead_time_hours: int,
        variable: str,
        model: str = "gfs_seamless",
    ) -> ForecastBustSignal:
        if not self.detector:
            return self._create_error(variable, lead_time_hours, "INSUFFICIENT_DATA")

        adapter = OpenMeteoEnsembleAdapter(model_name=model, member_prefix=model)
        loc = Location(name=location_name, latitude=latitude, longitude=longitude)

        req = ForecastRequest(
            location=loc,
            variables=[
                WeatherVariable(variable),
                WeatherVariable.TEMPERATURE_2M,
                WeatherVariable.PRECIPITATION,
                WeatherVariable.WIND_SPEED_10M,
            ],
            forecast_days=(lead_time_hours // 24) + 1,
        )

        try:
            results = await adapter.fetch_probabilistic_forecast(req, [])
        except Exception:
            return self._create_error(variable, lead_time_hours, "UNAVAILABLE")

        var_enum = WeatherVariable(variable)
        if var_enum not in results or not results[var_enum]:
            return self._create_error(variable, lead_time_hours, "UNAVAILABLE")

        time_series = results[var_enum]
        target_data = next(
            (
                prob_fcst
                for prob_fcst, _ in time_series
                if prob_fcst.lead_time_hours == lead_time_hours
            ),
            None,
        )

        if not target_data or target_data.status != "AVAILABLE":
            return self._create_error(variable, lead_time_hours, "INSUFFICIENT_DATA")

        # Causal Features
        features = {
            "lead_time_hours": lead_time_hours,
            "valid_member_count": target_data.valid_member_count,
            "model_disagreement": 0.0,
            "within_model_ensemble_spread": target_data.spread
            if target_data.spread is not None
            else 0.0,
            "regime_id": -1,
            "temperature_2m": 0.0,
            "precipitation": 0.0,
            "wind_speed_10m": 0.0,
        }

        # If it's a blended deterministic target, compute disagreement here
        if model == "ensemble":
            from forecast_forge.orchestrator.service import ForecastOrchestrator

            orch = ForecastOrchestrator()
            d_req = ForecastRequest(
                location=loc,
                variables=[WeatherVariable(variable)],
                forecast_days=(lead_time_hours // 24) + 1,
            )
            orch_res = await orch.fetch_all(d_req)
            vals = []
            for r in orch_res.values():
                if r.records:
                    closest = min(
                        r.records,
                        key=lambda x: (
                            abs(x.lead_time_hours - lead_time_hours)
                            if x.lead_time_hours is not None
                            else 999
                        ),
                    )
                    if closest.lead_time_hours == lead_time_hours:
                        val = getattr(closest, variable, None)
                        if val is not None:
                            vals.append(val)
            if vals:
                import statistics

                features["model_disagreement"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
                features["valid_member_count"] = len(vals)
                features["within_model_ensemble_spread"] = 0.0

        regime_context_str = None

        if self.regime_assigner:
            forecast_dict = {}
            for v in ["temperature_2m", "precipitation", "wind_speed_10m"]:
                enum_v = WeatherVariable(v)
                if enum_v in results:
                    v_data = next(
                        (p for p, _ in results[enum_v] if p.lead_time_hours == lead_time_hours),
                        None,
                    )
                    if v_data and v_data.mean is not None:
                        forecast_dict[v] = v_data.mean
                        features[v] = v_data.mean

            assignment = self.regime_assigner.assign_forecast_state(forecast_dict)
            if assignment.is_valid:
                features["regime_id"] = assignment.regime_id
                for r in self.regime_assigner.pipeline.regimes:
                    if r.regime_id == assignment.regime_id:
                        regime_context_str = f"Regime {r.regime_id}: {r.description}"
                        break

        signal, raw_factors, thresh = self.detector.predict_signal(features, variable)

        factors = [
            BustFactor(name=f["name"], contribution=f["contribution"], direction=f["direction"])
            for f in raw_factors
        ]

        return ForecastBustSignal(
            signal=signal,
            variable=variable,
            lead_time_hours=lead_time_hours,
            bust_threshold=thresh,
            historical_error_quantile=self.detector.quantile,
            primary_factors=factors,
            regime_context=regime_context_str,
            status="AVAILABLE",
        )

    def _create_error(self, variable: str, lead: float, status: str) -> ForecastBustSignal:
        return ForecastBustSignal(
            signal=status, variable=variable, lead_time_hours=lead, status=status
        )
