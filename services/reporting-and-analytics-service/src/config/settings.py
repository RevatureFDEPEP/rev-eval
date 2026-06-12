# src/config/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ALLOW_ORIGINS: str = "http://localhost:3000"
    SERVICE_NAME: str = "reporting-and-analytics-service"
    PORT: int = 8004
    LOG_LEVEL: str = "INFO"

    # Service-to-service: reporting aggregates submission/test data over HTTP
    # from test-management-service (compose-internal DNS).
    TEST_MANAGEMENT_URL: str = "http://test-management-service:8001"

    # Bound upstream calls so a slow/dead dependency cannot hang reporting.
    UPSTREAM_TIMEOUT_SECONDS: float = 10.0

    class Config:
        env_file = ".env"


settings = Settings()
