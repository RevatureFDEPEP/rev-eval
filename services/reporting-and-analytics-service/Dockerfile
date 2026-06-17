# Reporting and Analytics Service Dockerfile

# ─── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: test ────────────────────────────────────────────────────────────
FROM base AS test

COPY dev-requirements.txt .
RUN pip install --no-cache-dir -r dev-requirements.txt \
    && pip install --no-cache-dir pytest pytest-cov

COPY . .

RUN pytest -q --tb=short \
    && touch /tmp/.tests-passed


# ─── Stage 3: production ──────────────────────────────────────────────────────
FROM base AS production

COPY --from=test /tmp/.tests-passed /tmp/.tests-passed
RUN rm /tmp/.tests-passed

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

CMD ["python", "main.py"]
