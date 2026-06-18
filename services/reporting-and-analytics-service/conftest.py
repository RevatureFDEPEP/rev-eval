import os

# Must be set before any service module is imported (pydantic-settings reads env on class load).
# Own datastore (required fields):
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "reporting_test")
# Read-only TMS source (have defaults, set explicitly for clarity):
os.environ.setdefault("TMS_DB_HOST", "localhost")
os.environ.setdefault("TMS_DB_NAME", "tms_test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
