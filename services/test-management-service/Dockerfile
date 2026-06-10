# Test Management Service Dockerfile
#
# Multi-stage: base (runtime deps) -> test (dev deps + pytest gate) -> production.
# The default build target is the final `production` stage, so
# `docker compose up --build` is unchanged. Run the in-image test gate with
# `docker build --target test .` (the build fails if any unit test fails).
# The unit tests are hermetic (in-memory SQLite), so no Postgres is needed
# during the build.

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

# Copy requirements first for better caching
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

# Make startup script executable
RUN chmod +x start.sh

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the startup script
CMD ["./start.sh"]
