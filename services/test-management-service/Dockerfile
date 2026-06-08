# Test Management Service Dockerfile

FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Test stage: run unit tests before building production image
FROM deps AS test

COPY . .
ENV DB_HOST=test \
    DB_PORT=5432 \
    DB_USERNAME=test \
    DB_PASSWORD=test \
    DB_NAME=testdb \
    ALLOW_ORIGINS="*" \
    SERVICE_NAME=test-management-service \
    PORT=8001 \
    SERVICE_HOSTNAME=localhost \
    DATABASE_URL=postgresql://test:test@localhost:5432/testdb
RUN pytest tests/ -v --cov=src --cov-report=term-missing

# Production stage
FROM deps AS production

COPY . .
RUN chmod +x start.sh
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
CMD ["./start.sh"]
