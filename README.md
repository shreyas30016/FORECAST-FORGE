# Forecast Forge AI

An ensemble numerical weather prediction (NWP) decision-support system that blends multiple operational forecast models into evidence-based, uncertainty-aware guidance — with full decision provenance.

---

## Core Innovation

Forecast Forge AI adapts each model's contribution to the blended forecast according to **location × forecast lead time × weather regime**, using causally valid historical skill evidence (MAE/RMSE evaluated against ERA5 reanalysis benchmarks with strict forward-only temporal splits). This makes it a **decision-support layer** on top of existing NWP models — not a new forecast model itself — enabling quantified, reproducible justification for model weighting choices that are otherwise made subjectively.

---

## Problem

Operational weather forecasters using multiple NWP models (ECMWF IFS, NOAA GFS, ECMWF AIFS · AI Model) have no systematic way to determine which model to trust for a given location, lead time, or weather regime. Model skill varies by variable, geography, and atmospheric condition. Manual model selection is subjective, undocumented, and not reproducible.

---

## Solution

Forecast Forge AI continuously evaluates model skill against ERA5 reanalysis reference benchmarks using leakage-safe temporal alignment, then applies adaptive ensemble blending — weighted by verified historical error — to produce a unified forecast with explicit uncertainty indicators, regime context, and a full decision trace.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Adaptive Model Weighting** | Ridge regression ensemble; weights updated per variable, location, and lead-time using MAE/RMSE from verified history |
| **Spatial × Lead-Time Skill** | Weights vary by grid cell and forecast horizon — each lead-time bucket carries an independent skill evaluation |
| **Weather-Regime Intelligence** | K-Means clustering identifies atmospheric regimes; model skill is evaluated per regime to capture non-stationary model performance |
| **Probabilistic Guidance** | Spread-based uncertainty derived from disagreement across independent deterministic forecast sources; per-variable probability of exceedance |
| **Extreme-Weather Detection** | Threshold-based detection (heatwave, heavy precipitation, wind alert) with regime-conditioned probability |
| **Forecast-Bust Detection** | Logistic regression classifier trained on causal features (lead time, model disagreement, regime, weather state) to flag elevated bust risk before verification |
| **Scientific Replay** | Reconstructs historical forecast decisions from available archived snapshots with explicit EXACT / DEGRADED / UNAVAILABLE provenance |
| **Decision Trace** | Every blended output is linked to the historical snapshot, algorithm version, and weights used to produce it |
| **Nemotron Copilot** | NVIDIA Nemotron LLM assistant grounded strictly in retrieved trace context; refuses to invent data |

---

## Supported Forecast Sources

| Source | Model Identifier | Notes |
|---|---|---|
| ECMWF IFS | `ecmwf_ifs025` | Primary deterministic NWP model; 0.25° resolution |
| NOAA GFS | `gfs_seamless` | Global Forecast System; seamless blend of GFS cycles |
| ECMWF AIFS · AI Model | `ecmwf_aifs025` | ECMWF machine-learning forecast; third deterministic source |

All three are **deterministic forecast models** accessed via [Open-Meteo](https://open-meteo.com/). They are treated as independent forecast sources for ensemble blending — not as within-model ensemble members. The provider registry is extensible; new models can be added by implementing the `BaseWeatherAdapter` interface.

> **AIFS data availability note:** When ECMWF AIFS returns HTTP 200 with all-null variable values, the system reports `NO_VALID_DATA` for that provider. This reflects a limitation of the requested variable at the current resolution or time window — it does not imply a provider outage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 16 Frontend  (ui/)                                     │
│  Dashboard · Maps · Ensemble · Replay · Copilot                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │  HTTP / REST (FastAPI)
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI Backend  (forecast_forge/api/)                          │
│  /forecast  /ensemble  /evaluation  /replay  /agent/chat         │
└───────┬──────────┬──────────────┬──────────────┬────────────────┘
        │          │              │              │
   Providers  Ensemble        Evaluation     Replay
   open_meteo/ engine.py    scoring.py      service.py
   ifs / gfs   adaptive.py  weighting.py    registry.py
   /aifs       uncertainty  regimes/
                            bust/
                            lead_time_eval
        │          │              │              │
        └──────────┴──────────────┴──────────────┘
                       │
                  Trace & Provenance
                  trace/builder.py · storage.py
                       │
                  Nemotron Copilot
                  agent/runtime.py · tools.py
```

All components operate on a **canonical data schema** (`forecast_forge/core/models.py`) — provider-specific response shapes are translated in adapter classes and never leak into business logic.

---

## Scientific Integrity

- **ERA5 is a reanalysis reference benchmark**, not observational ground truth. All historical skill evaluations reference ERA5 reanalysis data as the verification baseline.
- **Multi-model disagreement ≠ within-model ensemble spread.** The spread reported by Forecast Forge AI is the standard deviation across independent deterministic NWP model outputs (IFS, GFS, AIFS). It is not derived from internal ensemble member distributions and should not be interpreted as a calibrated probability or confidence interval.
- **Unavailable data is never fabricated or silently substituted.** When a provider returns missing or unusable data, the system reports the canonical status (`NO_VALID_DATA`, `UNAVAILABLE`, `DEGRADED`) explicitly. No synthetic imputation is performed.
- **Historical evaluations follow strict causal / chronological rules.** Training features at time *T* use only information available at or before *T*. Time-series splits are strictly forward-only.
- **Inverse-error weighting is not Bayesian.** Weights are derived from rolling historical MAE/RMSE — a deterministic scoring method, not a probabilistic Bayesian update.
- **Replay accuracy is bounded by archived provenance.** The replay engine reconstructs past forecast decisions from stored provider snapshots and reports an explicit integrity status: `EXACT` when all source data is present, `DEGRADED` when partial, `UNAVAILABLE` when no archived snapshot exists.
- **No model is universally best.** Model skill varies by variable, geography, season, and atmospheric regime. Forecast Forge AI quantifies this variability rather than assuming any single model is superior.

---

## Validation Snapshot

Evaluation against ERA5 reanalysis reference benchmark on the included Mumbai sample dataset.

**Location:** Mumbai, India (19.076°N, 72.878°E)  
**Variable:** `temperature_2m`  
**Reference dataset:** ERA5 reanalysis (via Open-Meteo archive API)  
**Sample size:** 192 aligned forecast–reference pairs  
**Lead-time bucket:** Mixed (single bucket; lead-time-stratified evaluation available via `scripts/run_lead_time_evaluation.py`)

| Model / Blend | MAE (°C) | RMSE (°C) | Bias (°C) |
|---|---|---|---|
| ECMWF IFS (`ecmwf_ifs025`) | 0.36 | 0.47 | −0.05 |
| NOAA GFS (`gfs_seamless`) | 1.12 | 1.27 | +0.99 |
| Equal-weight blend | 0.39 | 0.48 | +0.32 |
| Inverse-error blend | 0.31 | 0.38 | +0.11 |
| Adaptive Ridge blend | 0.38 | 0.48 | −0.37 |

*Out-of-sample test set (39 rows, chronological split): Inverse-error weighting (RMSE 0.380) outperforms equal-weight (RMSE 0.481) and individual GFS (RMSE 0.889) on this sample. Results are specific to this location and period — not a universal performance claim.*

Reproduce with:
```bash
uv run python scripts/run_evaluation_report.py
uv run python scripts/run_ensemble_comparison.py
```

---

## Repository Structure

```
forecast-forge-ai/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example              # Environment variable template (no secrets)
├── pyproject.toml            # Python project definition and tool config
├── uv.lock                   # Locked dependency manifest
│
├── forecast_forge/           # Core Python backend
│   ├── agent/                # Nemotron Copilot runtime and tool definitions
│   ├── api/                  # FastAPI application, routes, and schemas
│   ├── core/                 # Canonical data models, enums, exceptions
│   ├── ensemble/             # Adaptive blending engine, uncertainty, explanations
│   ├── evaluation/           # Scoring, weighting, regime detection, bust detection
│   ├── extremes/             # Extreme-weather threshold detection
│   ├── historical/           # ERA5 reference data loading and temporal alignment
│   ├── orchestrator/         # End-to-end data-fetch pipeline
│   ├── providers/            # Open-Meteo adapters (IFS, GFS, AIFS · AI Model)
│   ├── replay/               # Temporal state reconstruction
│   ├── spatial/              # Geospatial grid operations and spatial weighting
│   ├── trace/                # Decision provenance builder and storage
│   └── validation/           # Physical bounds checking
│
├── ui/                       # Next.js 16 frontend
│   └── src/
│       ├── app/              # Page routes (forecast, ensemble, maps, replay, …)
│       ├── components/       # React components (charts, maps, copilot, …)
│       ├── context/          # React context providers
│       ├── lib/              # API client
│       └── types/            # TypeScript type definitions
│
├── tests/
│   ├── unit/                 # Pure unit tests (no network, no API keys)
│   ├── integration/          # Live-provider tests (skipped without API key)
│   └── api/                  # FastAPI endpoint integration tests
│
├── scripts/                  # Reproducibility and evaluation scripts
│
└── data/
    └── raw/
        └── mumbai_historical_sample.parquet   # Reproducibility seed (see below)
```

---

## Setup

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11 | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | Latest | Python package manager |
| Node.js | 18+ | Frontend |
| npm | 9+ | Frontend packages |

### Backend

```bash
# 1. Create project-local virtual environment
uv venv --python 3.11 .venv

# 2. Install all dependencies (including dev extras)
uv sync --extra dev

# 3. Configure environment
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY if using the Nemotron Copilot feature
```

### Frontend

```bash
cd ui
npm install
```

---

## Environment Variables

Copy `.env.example` to `.env` and populate as needed. See `.env.example` for all available variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ENV` | No | `development` | Execution environment |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `OPEN_METEO_BASE_URL` | No | `https://api.open-meteo.com/v1` | Open-Meteo forecast API |
| `NVIDIA_API_KEY` | Only for Copilot | — | NVIDIA Nemotron API key |
| `HTTP_TIMEOUT_SECONDS` | No | `10.0` | HTTP request timeout |
| `HTTP_MAX_RETRIES` | No | `3` | Retry attempts for transient failures |

**Never commit `.env` to version control.** The `.gitignore` excludes it. The Copilot feature gracefully degrades — all other capabilities function without `NVIDIA_API_KEY`.

---

## Running the Application

### Backend (FastAPI)

```bash
uv run uvicorn forecast_forge.api.app:app --reload --host 0.0.0.0 --port 8000
```

API documentation is available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Frontend (Next.js)

```bash
cd ui
npm run dev
```

Open `http://localhost:3000` in a browser.

---

## Testing

```bash
# Run all unit tests (no network access required)
uv run pytest tests/unit/ -v

# Run API integration tests
uv run pytest tests/api/ -v

# Run live Copilot integration tests (requires NVIDIA_API_KEY)
uv run pytest tests/integration/ -v -m integration

# Run full test suite
uv run pytest

# Run linter
uv run ruff check forecast_forge tests
```

Unit and API tests require no external credentials or network access. Integration tests are automatically skipped when `NVIDIA_API_KEY` is absent.

---

## Evaluation Scripts

Scripts are grouped by purpose. All use relative paths and write outputs to `data/processed/` (gitignored).

**Data acquisition**
```bash
# Fetch ERA5 historical reference data for a location
uv run python scripts/fetch_historical_mumbai.py
```

**Evaluation**
```bash
# Per-variable model skill report (MAE, RMSE, bias, inverse-error weights)
uv run python scripts/run_evaluation_report.py

# Compare equal-weight vs inverse-error vs adaptive Ridge blends
uv run python scripts/run_ensemble_comparison.py

# Ablation study across ensemble feature configurations
uv run python scripts/run_ablation_experiments.py
```

**Lead-time and regime**
```bash
# Per-lead-time skill evaluation with causal guards
uv run python scripts/run_lead_time_evaluation.py

# Discover and characterize weather regimes (K-Means)
uv run python scripts/run_regime_discovery.py

# Compare model skill across discovered regimes
uv run python scripts/run_regime_baseline_comparison.py
```

**Spatial**
```bash
# Spatial × lead-time weight grid evaluation
uv run python scripts/run_spatial_lead_time_evaluation.py
```

**Replay and smoke tests**
```bash
# Validate replay provenance registry
uv run python scripts/validate_replay.py

# Live FastAPI smoke test (requires running backend)
uv run python scripts/run_fastapi_smoke_test.py

# Live ensemble fetch from Open-Meteo (requires network)
uv run python scripts/run_live_ensemble.py
```

Input data (`data/raw/mumbai_historical_sample.parquet`) is a **small reproducibility seed** covering a single location and time window — sufficient to run all evaluation scripts and reproduce the metrics in the Validation Snapshot above. It is not a full historical archive; broader evaluation requires fetching additional data via `scripts/fetch_historical_mumbai.py` (adaptable to other locations).

---

## Deployment

### Local / Development

Start backend and frontend as described under **Running the Application**.

### Production

The final production architecture uses a split deployment:
- **Backend**: FastAPI API deployed on **Railway**
- **Frontend**: Next.js UI deployed on **Vercel**

For step-by-step instructions on deploying the full stack, configuring CORS, and setting up environment variables, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Known Limitations

- **Reproducibility seed covers Mumbai only.** `data/raw/mumbai_historical_sample.parquet` is a small sample for a single city and time window. The validation results above are specific to this sample and should not be extrapolated as general model rankings.
- **Open-Meteo rate limits.** Live fetches are subject to Open-Meteo's free-tier rate limits. The HTTP client implements exponential backoff; for production use, consider the Open-Meteo commercial API.
- **Replay accuracy depends on archived provenance.** The replay engine reports `EXACT` only when all source snapshots are present. Partial or absent archives yield `DEGRADED` or `UNAVAILABLE` status respectively.
- **Copilot requires NVIDIA API key.** The Nemotron Copilot is unavailable without a valid `NVIDIA_API_KEY`. All other system capabilities (ensemble, evaluation, maps, replay) function independently.
- **Bust detector requires pre-trained model.** The logistic regression bust classifier is loaded from `.model_cache/bust/`. Without a trained model file, the service returns `INSUFFICIENT_DATA`. Train it by running `scripts/run_evaluation_report.py` and the bust training step.
- **Adaptive model is trained on-demand.** The Ridge regression ensemble model is fitted lazily from stored historical data. Cold-start accuracy is limited until sufficient verified history accumulates.
- **AIFS variable coverage.** ECMWF AIFS via Open-Meteo may return null values for certain variables or time windows. The system reports `NO_VALID_DATA` in these cases and excludes AIFS from that blending step rather than substituting with another model.
- **Python 3.11 only.** The project currently targets Python 3.11 (`requires-python = ">=3.11,<3.12"`).

---

## License

See [LICENSE](LICENSE) for terms.
