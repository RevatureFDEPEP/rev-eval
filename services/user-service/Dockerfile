# User Service Dockerfile
#
# Multi-stage: base (system deps) -> deps (prod deps) -> test (dev deps + pytest gate) -> production.
# Default target is `production`. Run the in-image test gate with:
#   docker build --target test .
# Tests are hermetic (in-memory SQLite) — no Postgres needed.

FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===== deps: production dependencies only =====
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== test: dev deps + run the unit tests (build fails if a test fails) =====
FROM base AS test

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q

# ===== production (default target) =====
FROM deps AS production

COPY . .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
