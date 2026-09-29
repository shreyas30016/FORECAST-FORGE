FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies using standard pip for bulletproof compatibility
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the application itself
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE $PORT

# Start application
CMD ["sh", "-c", "uvicorn forecast_forge.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
