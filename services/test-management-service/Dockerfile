# test-management-service Dockerfile — three-stage build
# base  : shared OS deps + runtime Python packages
# test  : installs dev/test deps, runs pytest; build fails if tests fail
# production : clean final image with startup script + non-root user

FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY test-management-service/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel "jaraco.context>=6.1.0" && \
    pip install --no-cache-dir -r requirements.txt


FROM base AS test

COPY requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY test-management-service/ .

RUN pytest tests/ --tb=short -q


FROM base AS production

COPY test-management-service/ .

RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["./start.sh"]
