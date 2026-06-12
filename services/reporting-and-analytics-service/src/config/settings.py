# src/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (PostgreSQL — dedicated reporting datastore)
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str

    # Test-management-service Postgres (eval_ai_dev) — read-only source for
    # report queries. See docs/adr/0001-reporting-cross-service-data-access.md.
    # Defaults mirror the compose env for test-management-service.
    TMS_DB_HOST: str = "postgres"
    TMS_DB_PORT: int = 5432
    TMS_DB_USERNAME: str = "root"
    TMS_DB_PASSWORD: str = "root"
    TMS_DB_NAME: str = "eval_ai_dev"

    # JWT verification (defense-in-depth, W4-F3). Must match user-service's
    # signing key — the reporting service independently re-verifies the token
    # the gateway forwards instead of trusting X-User-* headers.
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Reporting (W4-F3): a session score (0–100) at or above this counts as a
    # pass in GET /reports/aggregate's pass-rate column.
    REPORT_PASS_THRESHOLD: float = 70.0

    # Service Configuration
    ALLOW_ORIGINS: str = "*"
    SERVICE_NAME: str = "reporting-and-analytics-service"
    PORT: int = 8004
    SERVICE_HOSTNAME: str = "reporting-and-analytics-service"
    LOG_LEVEL: str = "INFO"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def TMS_SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.TMS_DB_USERNAME}:{self.TMS_DB_PASSWORD}"
            f"@{self.TMS_DB_HOST}:{self.TMS_DB_PORT}/{self.TMS_DB_NAME}"
        )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
