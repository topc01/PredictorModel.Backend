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
RUN uv sync --frozen

COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
