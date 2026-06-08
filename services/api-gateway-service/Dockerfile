# API Gateway Service Dockerfile
#
# Multi-stage: base (runtime deps) -> test (dev deps + pytest gate) -> production.
# The default build target is the final `production` stage, so
# `docker compose up --build` is unchanged. Run the in-image test gate with
# `docker build --target test .` (the build fails if any unit test fails).

# ===== base: runtime dependencies =====
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
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

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]
