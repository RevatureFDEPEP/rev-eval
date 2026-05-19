"""
Configuration settings for notification service.
Loads environment variables using Pydantic Settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "eval_ai_dev"

    # Service Configuration
    SERVICE_NAME: str = "notification-service"
    PORT: int = 8004
    SERVICE_HOSTNAME: str = "127.0.0.1"

    # Consul Configuration (optional for AWS Cloud Map deployment)
    CONSUL_HOST: Optional[str] = None
    CONSUL_PORT: Optional[int] = None

    # AWS SES Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    SES_SENDER_EMAIL: str = "noreply@example.com"
    SES_SENDER_NAME: str = "Rev EvalAI"

    # Application Configuration
    FRONTEND_URL: str = "http://localhost:3000"
    INVITE_TOKEN_SECRET: str = "change-me-in-production"
    INVITE_TOKEN_EXPIRY_DAYS: int = 7

    # AWS SQS Configuration
    SQS_ENABLED: bool = True
    SQS_QUEUE_URL: str = ""
    SQS_POLLING_INTERVAL: int = 5  # Seconds between polls
    SQS_MAX_MESSAGES: int = 10  # Max messages to retrieve per poll
    SQS_WAIT_TIME_SECONDS: int = 20  # Long polling wait time
    SQS_VISIBILITY_TIMEOUT: int = 30  # Message visibility timeout in seconds

    # CORS
    ALLOW_ORIGINS: str = "http://localhost:3000"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.ALLOW_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
