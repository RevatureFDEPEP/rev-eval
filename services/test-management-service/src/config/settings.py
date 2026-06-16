# src/config/settings.py
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str
    MONGO_USER: Optional[str] = None  # Optional - service uses PostgreSQL only
    MONGODB_PASSWORD: Optional[str] = None  # Optional - service uses PostgreSQL only
    ALLOW_ORIGINS: str
    SERVICE_NAME: str
    PORT: int
    SERVICE_HOSTNAME: str

    # Service-to-Service Communication
    # Default to the user-service port (8002). The previous default pointed at
    # 8003 (question-service), so any non-compose run resolved user lookups to
    # the wrong service.
    USER_SERVICE_URL: str = "http://user-service:8002"
    QUESTION_SERVICE_URL: str = "http://question-management-service:8003"
    # Optional: interview transcript/evaluation integration. When unset, review
    # flows degrade gracefully (no transcript / skipped evaluation push) instead
    # of raising AttributeError.
    INTERVIEW_SERVICE_URL: Optional[str] = None

    # Shared secret presented to user-service on internal calls so they pass
    # its admin-guarded read endpoints without a user JWT. Must match
    # user-service's INTERNAL_API_KEY.
    INTERNAL_API_KEY: Optional[str] = None

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
