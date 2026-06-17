# src/config/settings.py
from typing import Optional
from pydantic_settings import BaseSettings

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

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
