import os

# Provide dummy DB env vars so pydantic-settings can instantiate Settings at import time.
# Tests in this suite only exercise pure logic (bcrypt, JWT) and never connect to a DB.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests")
