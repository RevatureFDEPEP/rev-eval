# src/config/settings.py
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings

# The value .env.example and docker-compose.yml use for local development. It is
# accepted only when APP_ENV=development.
DEV_INTERNAL_SERVICE_TOKEN = "change-me-internal-service-token"


def internal_token_allowed(token: Optional[str], app_env: str) -> bool:
    token = (token or "").strip()
    if not token:
        return False
    return token != DEV_INTERNAL_SERVICE_TOKEN or app_env.strip().lower() == "development"


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str
    MONGO_USER: Optional[str] = None
    MONGODB_PASSWORD: Optional[str] = None
    ALLOW_ORIGINS: str
    SERVICE_NAME: str
    PORT: int
    SERVICE_HOSTNAME: str

    JWT_SECRET: str = "change-me-in-production"

    # Service-to-Service Communication
    USER_SERVICE_URL: str = "http://localhost:8003"
    INTERVIEW_SERVICE_URL: Optional[str] = None
    QUESTION_SERVICE_URL: Optional[str] = "http://question-management-service:8003"
    # Sent only to question-management-service, which serves the question bank,
    # answer keys included, only to this service and to trainers.
    INTERNAL_SERVICE_TOKEN: Optional[str] = None

    # "development" allows the placeholder internal token; anything else
    # refuses to start with it.
    APP_ENV: str = "production"

    @model_validator(mode="after")
    def _refuse_dev_internal_token_outside_development(self):
        placeholder = (self.INTERNAL_SERVICE_TOKEN or "").strip() == DEV_INTERNAL_SERVICE_TOKEN
        if placeholder and self.APP_ENV.strip().lower() != "development":
            raise ValueError(
                "INTERNAL_SERVICE_TOKEN is the development placeholder; set a long random "
                "value, or APP_ENV=development for local development"
            )
        return self

    @property
    def internal_service_token(self) -> Optional[str]:
        """The token to use, or None when it must not be used: unset, empty, or
        the development placeholder outside APP_ENV=development."""
        token = (self.INTERNAL_SERVICE_TOKEN or "").strip()
        return token if internal_token_allowed(token, self.APP_ENV) else None

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
