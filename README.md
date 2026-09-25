# Forecast Forge AI

An ensemble numerical weather prediction (NWP) decision-support system designed for professional weather forecasters and analysts.

Forecast Forge AI compares multiple numerical weather prediction models (e.g., ECMWF IFS, NOAA GFS, ECMWF AIFS · AI Model), tracks provider availability and data health, evaluates model error patterns against reference datasets using leakage-safe temporal alignment, and produces an evidence-based blended forecast with explicit uncertainty indicators.

## Core Architectural Principles

- **Scientific Integrity**: Forecasts are never fabricated or synthetically imputed. When a model returns missing or null data, it is explicitly reported as `UNAVAILABLE` or `PARTIAL`.
- **Leakage-Safe Validation**: Training features at time $T$ only utilize information available at or before $T$. Time-series splits are strictly chronological.
- **Explainable Blending**: Models are weighted based on verified historical skill (MAE, RMSE, bias) and model disagreement rather than arbitrary manual weights.
- **Provider Abstraction**: Core logic operates on a canonical schema, decoupled from specific external provider response shapes.
- **Decision Provenance**: Every AI-driven synthesis and blended output traces back to the exact historical snapshot and algorithm version used to produce it.

## Repository Structure

```
forecast-forge-ai/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── pyproject.toml
├── uv.lock
├── forecast_forge/         # Core Python Backend
│   ├── agent/              # Forecast Copilot and LLM tools
│   ├── api/                # FastAPI application and routes
│   ├── ensemble/           # Blending and probabilistic models
│   ├── evaluation/         # Model scoring and metrics
│   ├── extremes/           # Extreme weather detection
│   ├── historical/         # Reference data loading and slicing
│   ├── orchestrator/       # End-to-end data pipelines
│   ├── providers/          # External weather API integrations
│   ├── replay/             # Temporal state reconstruction
│   ├── spatial/            # Geospatial manipulation
│   ├── trace/              # Decision provenance and logging
│   └── validation/         # Physical bounds checking
└── ui/                     # Next.js Frontend application
```

## Prerequisites

- **Python**: 3.11
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Node.js**: v18+ (for frontend)

## Quickstart

### 1. Set Up Backend

```bash
# Create project-local virtual environment with Python 3.11
uv venv --python 3.11 .venv

# Install dependencies
uv sync --extra dev

# Copy the example environment configuration
cp .env.example .env
```

### 2. Set Up Frontend

```bash
cd ui
npm install
```

### 3. Run Verification & Tests

```bash
# Run the Python test suite
uv run pytest

# Run linter checks
uv run ruff check .
```
