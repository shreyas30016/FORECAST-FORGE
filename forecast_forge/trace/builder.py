"""Builder for constructing DecisionTrace provenance."""

import uuid
from datetime import UTC, datetime

from forecast_forge.core.enums import WeatherVariable
from forecast_forge.core.models import Location
from forecast_forge.replay.schemas import ReplaySnapshot
from forecast_forge.trace.schemas import (
    BustTrace,
    DecisionTrace,
    ExtremeGuidanceTrace,
    ProbabilisticTrace,
    RegimeTrace,
    TraceContext,
    TraceForecast,
    VerificationTrace,
    WeightEvidence,
)


class TraceBuilder:
    """Builds a deterministic DecisionTrace from forecast components."""

    @staticmethod
    def from_replay_snapshot(snapshot: ReplaySnapshot) -> DecisionTrace:
        """Constructs a full DecisionTrace from a ReplaySnapshot."""

        decision = snapshot.forecast_time_decision

        # 1. Trace Context
        context = TraceContext(
            variable=WeatherVariable(snapshot.variable),
            valid_time=decision.valid_time,
            lead_time_hours=decision.lead_time_hours,
            forecast_run=decision.initialization_time,
        )

        # 2. Forecast Decision
        forecast = TraceForecast(
            value=decision.final_blended_value,
            unit="metric",  # Assume metric for now
            status=decision.data_quality_status,
            source=decision.provenance,
            valid_time=decision.valid_time,
            provenance="Blended Ensemble"
            if decision.final_blended_value is not None
            else "Missing Data",
        )

        # 3. Model Inputs
        model_inputs = decision.model_forecasts.copy()

        # 4. Weights Evidence
        weights_evidence = []
        for model, weight in decision.spatial_weights.items():
            # Since we use a safe fallback, we explicitly document this in the evidence.
            # If we had real RMSE, we'd pull it from the snapshot's weight metadata.
            weights_evidence.append(
                WeightEvidence(
                    model=model,
                    weight=weight,
                    weight_method="safe_fallback_uniform",
                    rmse=None,
                    mae=None,
                    bias=None,
                    sample_count=None,
                    spatial_scope="global_fallback",
                    lead_time_hours=decision.lead_time_hours,
                    status="UNAVAILABLE_EXACT_REGISTRY",
                    provenance="Fallback weight (No temporal registry)",
                )
            )

        # 5. Regime Trace
        if decision.regime:
            regime = RegimeTrace(
                regime_id=decision.regime.regime_id,
                description=f"Regime {decision.regime.regime_id}",
                model_version=decision.regime.regime_model_version,
                feature_snapshot=decision.regime.feature_snapshot,
                scaler_version=None,
                assignment_timestamp=decision.initialization_time,
                causal_cutoff=decision.regime.causal_cutoff,
                model_hash=decision.regime.model_hash,
                status="AVAILABLE",
                provenance=decision.regime.assignment_provenance,
            )
        else:
            regime = RegimeTrace(
                regime_id=None, status="UNAVAILABLE", provenance="No regime available at T0"
            )

        # 6. Probabilistic
        if decision.probabilistic_status == "AVAILABLE":
            probabilistic = ProbabilisticTrace(
                model="ensemble",
                member_count=0,
                valid_member_count=0,
                status="AVAILABLE",
                provenance=decision.probabilistic_summary.get("reason", "Unknown"),
            )
        else:
            probabilistic = ProbabilisticTrace(
                model="ensemble",
                member_count=0,
                valid_member_count=0,
                status="UNAVAILABLE",
                provenance=decision.probabilistic_summary.get("reason", "API limitation"),
            )

        # 7. Extreme Guidance
        extremes = []
        for ext in decision.extreme_guidance:
            extremes.append(
                ExtremeGuidanceTrace(
                    event_type=ext.event_type,
                    variable=snapshot.variable,
                    operator=">=",
                    threshold=ext.threshold,
                    probability=ext.probability,
                    valid_member_count=None,
                    total_member_count=None,
                    probability_method="ensemble_member_frequency",
                    status=ext.status,
                    provenance=ext.provenance,
                )
            )

        # 8. Bust Signal
        bust_snap = decision.bust_signal
        bust = BustTrace(
            signal=bust_snap.signal,
            threshold=None,
            threshold_quantile=None,
            lead_time=decision.lead_time_hours,
            feature_snapshot=None,
            feature_contributions=None,
            model_version=bust_snap.model_version,
            training_cutoff=bust_snap.causal_cutoff,
            model_hash=bust_snap.model_hash,
            status="AVAILABLE" if bust_snap.signal != "UNAVAILABLE" else "UNAVAILABLE",
            provenance=bust_snap.provenance,
        )

        # 9. Verification
        if snapshot.later_verification:
            verif = VerificationTrace(
                reference_value=snapshot.later_verification.reference_value,
                error=snapshot.later_verification.realized_error,
                reference_source=snapshot.later_verification.reference_source,
                status="AVAILABLE"
                if snapshot.later_verification.reference_value is not None
                else "PENDING",
            )
        else:
            verif = VerificationTrace(
                reference_source="ERA5 reanalysis reference benchmark", status="PENDING"
            )

        location = Location(
            name="ReplayLocation", latitude=snapshot.latitude, longitude=snapshot.longitude
        )

        trace_id = str(uuid.uuid4())

        return DecisionTrace(
            trace_id=trace_id,
            created_at=datetime.now(UTC),
            location=location,
            request_context=context,
            decision_integrity=decision.replay_integrity_status,
            forecast=forecast,
            model_inputs=model_inputs,
            weights=weights_evidence,
            regime=regime,
            probabilistic=probabilistic,
            extreme_guidance=extremes,
            bust_signal=bust,
            verification=verif,
            limitations=[decision.probabilistic_summary.get("reason", "")],
        )
