"""Real smoke test for Phase 4.5 FastAPI layer."""

import json

from fastapi.testclient import TestClient

from forecast_forge.api.app import app


def run_smoke_test():
    client = TestClient(app)

    print("\n============================================================")
    print("1. /api/v1/health")
    res = client.get("/api/v1/health")
    print(json.dumps(res.json(), indent=2))

    print("\n============================================================")
    print("2. /api/v1/models")
    res = client.get("/api/v1/models")
    print(json.dumps(res.json(), indent=2))

    print("\n============================================================")
    print("3. /api/v1/ensemble (Real Mumbai Fetch)")
    # This will genuinely hit Open-Meteo through the Orchestrator
    res = client.get(
        "/api/v1/ensemble",
        params={
            "latitude": 19.0760,
            "longitude": 72.8777,
            "name": "Mumbai",
            "horizon_hours": 72,
            "variable": "temperature_2m",
        },
    )

    data = res.json()
    print("Status Code:", res.status_code)

    if res.status_code == 200:
        print("\nLocation:", data["location"]["name"])
        print("Valid Time:", data["valid_time"])
        print("\nMODELS:")
        for m, mf in data["models"].items():
            print(
                f"  {m}: status={mf['status']}, forecast={mf['forecast']}, weight={mf['weight']:.3f}"
            )

        print("\nENSEMBLE:")
        print(
            f"  forecast={data['ensemble']['forecast']}, spread={data['ensemble']['uncertainty']}, data_quality={data['ensemble']['data_quality']}"
        )
    else:
        print("ERROR:", json.dumps(data, indent=2))


if __name__ == "__main__":
    run_smoke_test()
