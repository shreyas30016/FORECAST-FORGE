import asyncio

import pandas as pd

from forecast_forge.spatial.grid_service import build_spatial_lead_time_weights_grid


async def main():
    print("--- SPATIAL x LEAD-TIME SKILL AUDIT ---")

    center_lat = 19.0760
    center_lon = 72.8777
    grid_size = 3

    # We will test a few lead times for Mumbai
    lead_times = [24.0, 72.0, 168.0]

    all_results = []

    for lead in lead_times:
        print(f"\nEvaluating Lead Time: {lead}h")
        res = await build_spatial_lead_time_weights_grid(
            center_lat=center_lat,
            center_lon=center_lon,
            lead_time_hours=lead,
            variable="temperature_2m",
            grid_size=grid_size,
            step=0.25,
            evaluation_mode="RETROSPECTIVE"
        )

        print(f"Status: {res.status}")
        for c in res.cells:
            if c.status == "AVAILABLE":
                all_results.append({
                    "lat": c.latitude,
                    "lon": c.longitude,
                    "model": c.model,
                    "lead_time": c.lead_time_hours,
                    "RMSE": c.rmse,
                    "Weight": c.weight,
                    "Samples": c.sample_count,
                    "Status": c.status
                })

    df = pd.DataFrame(all_results)
    if not df.empty:
        print("\nReal Spatial x Lead-Time Weights:")
        # Sort by lat, lon, lead_time, model
        df = df.sort_values(by=["lat", "lon", "lead_time", "model"])
        print(df.to_string(index=False))

        # Verify variation across space and time
        print("\nVerifying Variation:")
        ifs_24_weights = df[(df["model"] == "ecmwf_ifs025") & (df["lead_time"] == 24.0)]["Weight"].tolist()
        ifs_168_weights = df[(df["model"] == "ecmwf_ifs025") & (df["lead_time"] == 168.0)]["Weight"].tolist()

        if len(set(ifs_24_weights)) > 1:
            print("PASS: IFS 24h weights vary across space")
        else:
            print("NOTE: IFS 24h weights are uniform across space (could be data limitation)")

        if sum(ifs_24_weights) != sum(ifs_168_weights):
            print("PASS: IFS weights vary across lead time (24h vs 168h)")
        else:
            print("NOTE: IFS weights do not vary across lead time")

    else:
        print("No valid results found.")

if __name__ == "__main__":
    asyncio.run(main())
