FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*


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
    pip install --upgrade wheel setuptools && \
    apt-get purge -y --auto-remove gcc linux-libc-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=test /app/src ./src
COPY --from=test /app/main.py .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
