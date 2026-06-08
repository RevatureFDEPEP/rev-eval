FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Keep base-image Python tooling current: the bundled pip/setuptools/wheel
# lag upstream, so the Trivy gate (CRITICAL/HIGH, ignore-unfixed) can trip on
# fixable tooling CVEs whenever the base image drifts.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel


# ---- test stage ----
FROM base AS test

COPY requirements.txt dev-requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r dev-requirements.txt

COPY . .

RUN if [ -d tests ]; then pytest tests/ --tb=short || [ "$?" -eq 5 ]; fi


# ---- production stage ----
FROM base AS production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc linux-libc-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=test /app/src ./src
COPY --from=test /app/main.py .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
