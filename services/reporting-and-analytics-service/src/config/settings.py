# src/config/settings.py
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "eval_ai_dev"
    ALLOW_ORIGINS: str = "http://localhost:3000"
    SERVICE_NAME: str = "reporting-and-analytics-service"
    PORT: int = 8004
    SERVICE_HOSTNAME: str = "localhost"

    # Source service that owns the authoritative session data (see ADR 0001).
    TEST_MANAGEMENT_SERVICE_URL: Optional[str] = "http://localhost:8001"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
