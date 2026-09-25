"""Live smoke test of the ensemble engine."""

import asyncio

from forecast_forge.config import get_settings
from forecast_forge.core.models import ForecastRequest, Location
from forecast_forge.ensemble.engine import generate_ensemble_forecast
from forecast_forge.ensemble.schemas import EnsembleWeight, ModelForecast
from forecast_forge.logging_config import configure_logging
from forecast_forge.orchestrator.service import ForecastOrchestrator


async def main():
    settings = get_settings()
    configure_logging(settings.log_level)

    orchestrator = ForecastOrchestrator()
    mumbai = Location(latitude=19.0760, longitude=72.8777, name="Mumbai")
    req = ForecastRequest(location=mumbai)

    print("Fetching live forecast data from providers...")
    results = await orchestrator.fetch_all(req)

    if not results:
        print("No results returned.")
        return

    first_provider_res = list(results.values())[0]
    if not first_provider_res.records:
        print("No records found.")
        return

    target_time = first_provider_res.records[0].timestamp
    variable = "temperature_2m"

    forecasts = []

    for model_name, res in results.items():
        # Find the matching time record
        record = next((r for r in res.records if r.timestamp == target_time), None)
        if record and getattr(record, variable, None) is not None:
            forecasts.append(
                ModelForecast(
                    model=model_name,
                    value=getattr(record, variable),
                    is_valid=True,
                    status="AVAILABLE",
                )
            )
        else:
            # Missing or null
            forecasts.append(
                ModelForecast(
                    model=model_name, value=None, is_valid=False, status="NO_VALID_DATA"
                )
            )

    # Dummy historical weights for demonstration based on Phase 3
    weights = [
        EnsembleWeight(model="ecmwf_ifs025", weight=0.73),
        EnsembleWeight(model="gfs_seamless", weight=0.27),
    ]

    print(f"\nGenerating Ensemble for {target_time} - Variable: {variable}")
    ensemble_res = generate_ensemble_forecast(
        location_name=mumbai.name,
        variable=variable,
        valid_time=target_time.replace(tzinfo=None),  # Engine uses naive
        forecasts=forecasts,
        historical_weights=weights,
        expected_total_models=3,
    )

    print("\n--- ENSEMBLE RESULT ---")
    for mf in ensemble_res.model_forecasts:
        print(f"{mf.model}:")
        val_str = f"{mf.value:.1f}" if mf.value is not None else "null"
        print(f"forecast: {val_str}")
        print(f"status: {mf.status}")

        # calculate effective weight
        weight = 0.0
        if ensemble_res.adaptive_weights:
            weight = next(
                (w.weight for w in ensemble_res.adaptive_weights if w.model == mf.model), 0.0
            )
        elif weights and mf.is_valid:
            valid_models = {f.model for f in ensemble_res.model_forecasts if f.is_valid}
            total = sum(w.weight for w in weights if w.model in valid_models)
            if total > 0:
                raw = next((w.weight for w in weights if w.model == mf.model), 0.0)
                weight = raw / total

        # The user requested exactly "effective_weight: 0" for AIFS
        if weight == 0.0:
            print("effective_weight: 0\n")
        else:
            print(f"effective_weight: {weight:.3f}\n")

    print(f"Equal Weight: {ensemble_res.equal_weight_forecast:.2f}")
    print(f"Inverse Error: {ensemble_res.inverse_error_forecast:.2f}")
    if ensemble_res.uncertainty.spread is not None:
        print(f"Uncertainty Spread (StdDev): {ensemble_res.uncertainty.spread:.3f}")
    else:
        print("Uncertainty Spread: None")
    print(f"Data Quality: {ensemble_res.uncertainty.data_quality_indicator}")
    print(f"Explanation: {ensemble_res.explanation.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())
