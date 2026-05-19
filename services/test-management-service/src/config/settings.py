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
    CONSUL_HOST: Optional[str] = None
    CONSUL_PORT: Optional[int] = None
    SERVICE_HOSTNAME: str

    # Service-to-Service Communication
    USER_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8004"
    INTERVIEW_SERVICE_URL: str = "http://localhost:8006"

    # AWS SQS Configuration
    AWS_REGION: str = "us-west-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    SQS_QUEUE_URL: str = ""
    SQS_ENABLED: bool = True

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
