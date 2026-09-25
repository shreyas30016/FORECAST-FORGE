import asyncio
from datetime import UTC, datetime

from forecast_forge.replay.service import ReplayService


async def run_validation():
    service = ReplayService()
    run_time = datetime(2026, 9, 15, 0, 0, tzinfo=UTC)

    print("Running Scientific Replay for Mumbai (19.0760, 72.8777) at T0=", run_time)
    res = await service.get_replay_timeline(
        latitude=19.0760,
        longitude=72.8777,
        run_time=run_time,
        variable="temperature_2m"
    )

    # print full json dict representation of first snapshot
    if len(res.snapshots) > 0:
        print("\nFIRST SNAPSHOT JSON:", res.snapshots[0].model_dump_json(indent=2))

    print("\nTotal Snapshots:", len(res.snapshots))
    for s in res.snapshots:
        print("\n===============================")
        print(f"Lead Time: +{s.forecast_time_decision.lead_time_hours}h")
        print(f"Final Blend: {s.forecast_time_decision.final_blended_value}")
        print(f"Provenance: {s.forecast_time_decision.provenance}")
        print(f"Probabilistic Status: {s.forecast_time_decision.probabilistic_status}")

        reg = s.forecast_time_decision.regime
        if reg:
            print(f"Regime: {reg.regime_id} (version: {getattr(reg, 'regime_model_version', 'N/A')})")
        else:
            print("Regime: N/A")

        print(f"Bust Signal: {s.forecast_time_decision.bust_signal.signal}")
        print(f"Realized Reference: {s.later_verification.reference_value}")
        print(f"Realized Error: {s.later_verification.realized_error}")

if __name__ == "__main__":
    asyncio.run(run_validation())
