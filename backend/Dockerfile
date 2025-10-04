FROM python:3.11-slim AS base

# Configuración general
WORKDIR /app

# Instalar curl (necesario para uv) y limpiar cache
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Instalar UV (gestor de dependencias ultra rápido)
RUN pip install --no-cache-dir uv

# Copiar archivo de configuración de proyecto (aún sin dependencias)
COPY pyproject.toml ./

# Instalar dependencias base (por ahora vacías)
RUN uv sync

# Copiar código fuente
COPY src ./src

# Exponer el puerto de FastAPI
EXPOSE 8000

# Comando por defecto (usado en desarrollo, con hot reload)
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
