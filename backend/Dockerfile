FROM python:3.11-slim AS base

WORKDIR /app

# Update packages and install curl
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment
RUN uv sync --frozen --no-dev

# Copy application code
COPY src ./src

EXPOSE 8000

# Use the installed virtualenv directly (no uv run at runtime)
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
