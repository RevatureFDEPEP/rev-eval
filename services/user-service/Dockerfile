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
    DB_NAME=testdb
RUN pytest tests/ -v --cov=src --cov-report=term-missing

# Production stage
FROM deps AS production

COPY . .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
