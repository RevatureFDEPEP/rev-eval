FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
# Upgrade base-image Python tooling first: python:3.11-slim ships pip,
# wheel and jaraco.context versions with fixable CVEs that the Trivy CI
# gate (CRITICAL/HIGH, ignore-unfixed) rejects.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel "jaraco.context>=6.1.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
