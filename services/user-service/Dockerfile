# User Service Dockerfile
#
# Multi-stage: base (runtime deps) -> test (dev deps + pytest gate) -> production.
# The default build target is the final `production` stage, so
# `docker compose up --build` is unchanged. Run the in-image test gate with
# `docker build --target test .` (the build fails if any unit test fails).

# ===== base: runtime dependencies =====
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies.
# apt-get upgrade patches OS-package CVEs (e.g. libssl3t64 CVE-2026-45447, HIGH)
# that land in Debian before the python:3.11-slim base image rebuilds; the Trivy
# CI gate (CRITICAL/HIGH, ignore-unfixed) rejects them otherwise.
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
# Upgrade base-image Python tooling first: python:3.11-slim ships pip,
# wheel and jaraco.context versions with fixable CVEs that the Trivy CI
# gate (CRITICAL/HIGH, ignore-unfixed) rejects.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel "jaraco.context>=6.1.0" && \
    pip install --no-cache-dir -r requirements.txt

# ===== test: dev deps + run the unit tests (build fails if a test fails) =====
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q

# ===== production (default target) =====
FROM base AS production

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
