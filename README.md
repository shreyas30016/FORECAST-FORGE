# Forecast Forge AI

An ensemble numerical weather prediction (NWP) decision-support system that blends multiple operational forecast models into evidence-based, uncertainty-aware guidance — with full decision provenance.

---

## Problem

Operational weather forecasters using multiple NWP models (ECMWF IFS, NOAA GFS, ECMWF AIFS) have no systematic way to determine which model to trust for a given location, lead time, or weather regime. Model skill varies by variable, geography, and atmospheric condition. Manual model selection is subjective, undocumented, and not reproducible.

---

## Solution

Forecast Forge AI continuously evaluates model skill against ERA5 reanalysis reference benchmarks using leakage-safe temporal alignment, then applies adaptive ensemble blending — weighted by verified historical error — to produce a unified forecast with explicit uncertainty indicators, regime context, and a full decision trace.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Adaptive Model Weighting** | Ridge regression ensemble; weights updated per variable, location, and lead-time using MAE/RMSE from verified history |
| **Spatial × Lead-Time Skill** | Weights vary by grid cell and forecast horizon — closer lead times carry independent evaluations |
| **Weather-Regime Intelligence** | K-Means clustering identifies atmospheric regimes; model skill is evaluated per regime to capture non-stationary model performance |
| **Probabilistic Guidance** | Spread-based uncertainty from multi-model disagreement; per-variable probability of exceedance |
| **Extreme-Weather Detection** | Threshold-based detection (heatwave, heavy precipitation, wind alert) with regime-conditioned probability |
| **Forecast-Bust Detection** | Detects abnormal model divergence from climatology and flags potential bust conditions before verification |
| **Scientific Replay** | Reconstructs the exact forecast state at any past valid-time using archived provider snapshots |
| **Decision Trace** | Every blended output is linked to the historical snapshot, algorithm version, and weights used to produce it |
| **Nemotron Copilot** | NVIDIA Nemotron LLM assistant grounded strictly in retrieved trace context; refuses to invent data |

---

## Supported Forecast Sources

| Source | Model Identifier | Notes |
|---|---|---|
| ECMWF IFS | `ecmwf_ifs025` | Primary deterministic model; 0.25° resolution |
| NOAA GFS | `gfs_seamless` | Global Forecast System; seamless blend of GFS cycles |
| ECMWF AIFS | `ecmwf_aifs025` | AI-based ECMWF model; included as a third ensemble member |

All sources are accessed via [Open-Meteo](https://open-meteo.com/) — an open, free API requiring no authentication. The provider registry is extensible; new models can be added by implementing the `BaseWeatherAdapter` interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js Frontend  (ui/)                                        │
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
- **Model disagreement ≠ within-model ensemble spread.** Spread in Forecast Forge AI reflects disagreement across independent deterministic NWP models (IFS, GFS, AIFS), not internal ensemble member spread.
- **Unavailable data is never fabricated or silently substituted.** When a provider returns missing data, the system reports `UNAVAILABLE` or `PARTIAL` status explicitly. No synthetic imputation is performed.
- **Historical evaluations follow strict causal / chronological rules.** Training features at time *T* use only information available at or before *T*. Time-series splits are strictly forward-only.
- **Inverse-error weighting is not Bayesian.** Weights are derived from rolling historical MAE/RMSE — this is a deterministic scoring method, not a probabilistic Bayesian update.
- **Replay exactness depends on available provenance.** The replay engine reconstructs past forecast states from stored snapshots. Accuracy is bounded by what was archived at that time.
- **No model is universally best.** Model skill varies by variable, geography, season, and atmospheric regime. Forecast Forge AI quantifies this variability rather than assuming any single model is superior.

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
│   ├── providers/            # Open-Meteo adapters (IFS, GFS, AIFS, ensemble)
│   ├── replay/               # Temporal state reconstruction
│   ├── spatial/              # Geospatial grid operations and spatial weighting
│   ├── trace/                # Decision provenance builder and storage
│   └── validation/           # Physical bounds checking
│
├── ui/                       # Next.js 15 frontend
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
│   ├── run_evaluation_report.py
│   ├── run_ensemble_comparison.py
│   ├── run_lead_time_evaluation.py
│   ├── run_regime_discovery.py
│   └── …
│
└── data/
    └── raw/
        └── mumbai_historical_sample.parquet   # ERA5-derived sample (open-source)
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

Reproduce the published evaluation results:

```bash
# Generate evaluation report from historical sample data
uv run python scripts/run_evaluation_report.py

# Compare ensemble blending strategies
uv run python scripts/run_ensemble_comparison.py

# Evaluate per-lead-time model skill
uv run python scripts/run_lead_time_evaluation.py

# Discover and characterize weather regimes
uv run python scripts/run_regime_discovery.py

# Spatial × lead-time weighting evaluation
uv run python scripts/run_spatial_lead_time_evaluation.py
```

Input data (`data/raw/mumbai_historical_sample.parquet`) is included in the repository. Generated outputs are written to `data/processed/` (gitignored — regenerate locally).

---

## Deployment

### Local / Development

Start backend and frontend as described above.

### Production (Render)

A `render.yaml` configuration is provided for [Render](https://render.com/) deployment. Set environment variables via the Render dashboard — never in source code.

---

## Known Limitations

- **Single-city historical sample.** The included `data/raw/` sample covers Mumbai only. Broader spatial evaluation requires fetching additional ERA5 data via `scripts/fetch_historical_mumbai.py` (adaptable to other locations).
- **Open-Meteo rate limits.** Live fetches are subject to Open-Meteo's free-tier rate limits. The HTTP client implements exponential backoff; for production use, consider the Open-Meteo commercial API.
- **Replay completeness.** Scientific replay accuracy depends on what provider snapshots were stored at the time of the original forecast run. The replay engine reports `PARTIAL` status when snapshots are incomplete.
- **Copilot requires NVIDIA API key.** The Nemotron Copilot is unavailable without a valid `NVIDIA_API_KEY`. All other system capabilities (ensemble, evaluation, maps, replay) function independently.
- **Adaptive model is trained on-demand.** The Ridge regression ensemble model is fitted lazily from stored historical data. Cold-start accuracy is lower until sufficient verified history accumulates.
- **Python 3.11 only.** The project currently targets Python 3.11 (`requires-python = ">=3.11,<3.12"`).

---

## License

See [LICENSE](LICENSE) for terms.
