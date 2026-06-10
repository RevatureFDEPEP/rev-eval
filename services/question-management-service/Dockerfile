# Question Management Service Dockerfile

# ─── Stage 1: base ────────────────────────────────────────────────────────────
# OS packages and production Python dependencies shared by all later stages.
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: test ────────────────────────────────────────────────────────────
# Installs dev dependencies and runs the full test suite.
# A non-zero pytest exit code aborts the build here, before the production
# image is assembled.
FROM base AS test

COPY dev-requirements.txt .
RUN pip install --no-cache-dir -r dev-requirements.txt \
    && pip install --no-cache-dir pytest pytest-cov

COPY . .

RUN pytest -q --tb=short \
    && touch /tmp/.tests-passed


# ─── Stage 3: production ──────────────────────────────────────────────────────
# Lean production image built on the clean base layer.
# The COPY --from=test forces BuildKit to complete the test stage first;
# the sentinel file is removed so it does not persist in the final image.
FROM base AS production

COPY --from=test /tmp/.tests-passed /tmp/.tests-passed
RUN rm /tmp/.tests-passed

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["python", "main.py"]
