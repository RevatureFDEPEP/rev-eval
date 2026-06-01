# Test Management Service Dockerfile
# NOTE: This Dockerfile was updated to make the service robust in the
# compose environment and to support its database and SQS integration during
# development. Key reasons for edits:
# - Include `postgresql-client` so healthchecks and local debugging can use `psql`/tools.
# - Install minimal build-time deps and set up a non-root user for safer runtime.
# - Add a healthcheck so orchestrators and the API gateway can wait for readiness.
# The file describes application container choices, not unit/integration test code.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application directly
CMD ["python", "main.py"]
