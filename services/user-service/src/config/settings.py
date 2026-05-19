# src/config/settings.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database (PostgreSQL)
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str

    # Service Configuration
    ALLOW_ORIGINS: str = "*"
    SERVICE_NAME: str = "user-service"
    PORT: int = 8002

    SERVICE_HOSTNAME: str = "user-service"

    # WorkOS
    WORKOS_API_KEY: Optional[str] = None
    WORKOS_CLIENT_ID: Optional[str] = None

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
