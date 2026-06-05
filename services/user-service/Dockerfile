# user-service Dockerfile — three-stage build
# base  : shared OS deps + runtime Python packages
# test  : installs dev/test deps, runs pytest; build fails if tests fail
# production : clean final image with no test tooling

FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt


FROM base AS test

COPY ../requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

RUN pytest tests/ --tb=short -q


FROM base AS production

COPY . .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
