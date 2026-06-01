# Question Management Service Dockerfile
# NOTE (human): This Dockerfile was updated to ensure consistent runtime
# behavior inside the compose environment. Changes include:
# - Using a slim Python base image for smaller size.
# - Installing minimal system dependencies needed for wheels and runtime (gcc, curl).
# - Adding a healthcheck and running as a non-root user so the container behaves
#   correctly with `docker-compose` health checks and security best-practices.
# These edits help the `api-gateway` detect service readiness and reduce surprises
# when running the full stack locally or in CI.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
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
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the application directly
CMD ["python", "main.py"]
