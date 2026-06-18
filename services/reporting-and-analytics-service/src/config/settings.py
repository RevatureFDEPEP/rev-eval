# src/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (PostgreSQL) — this service's OWN datastore. It currently holds
    # no domain tables (reporting reads from test-management over the TMS engine
    # below); the own DB exists so this service has an independent Alembic chain
    # / alembic_version that never collides with test-management's in eval_ai_dev.
    # See docs/adr/0001-reporting-cross-service-data-access.md.
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str

    # Test-management-service Postgres (eval_ai_dev) — READ-ONLY source for
    # report queries (sessions / quiz_answers / tests). Defaults mirror the
    # compose env for test-management-service.
    TMS_DB_HOST: str = "postgres"
    TMS_DB_PORT: int = 5432
    TMS_DB_USERNAME: str = "root"
    TMS_DB_PASSWORD: str = "root"
    TMS_DB_NAME: str = "eval_ai_dev"

    # JWT verification (defense-in-depth, W4-F3): the trainer endpoints will
    # independently re-verify the gateway-forwarded token. Must match
    # user-service's signing key.
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"

    # W4-F3: a session score (0–100) at or above this counts as a pass.
    REPORT_PASS_THRESHOLD: float = 70.0

    ALLOW_ORIGINS: str = "http://localhost:3000"
    SERVICE_NAME: str = "reporting-and-analytics-service"
    PORT: int = 8004
    SERVICE_HOSTNAME: str = "reporting-and-analytics-service"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
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
