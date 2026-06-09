# src/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (PostgreSQL — dedicated reporting datastore)
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str

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

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
