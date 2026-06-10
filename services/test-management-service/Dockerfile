# Test Management Service Dockerfile
#
# Multi-stage: base (system deps) -> deps (prod deps) -> test (dev deps + pytest gate) -> production.
# Default target is `production`. Run the in-image test gate with:
#   docker build --target test .
# Tests are hermetic (in-memory SQLite via aiosqlite) — no Postgres needed.

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

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q

# ===== production (default target) =====
FROM deps AS production

COPY . .
RUN chmod +x start.sh
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
CMD ["./start.sh"]
