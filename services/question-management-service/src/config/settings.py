# src/config/settings.py
from typing import Optional
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All MongoDB credentials are properly URL-encoded to handle special characters.
    """
    # MongoDB Configuration
    MONGO_USER: str
    MONGODB_PASSWORD: str
    MONGO_CLUSTER: str
    MONGO_APPNAME: str
    MONGO_DB: str

    # Service Configuration
    ALLOW_ORIGINS: str = "*"
    SERVICE_NAME: str
    PORT: int = 8002
    SERVICE_HOSTNAME: str = "localhost"

    # Optional MongoDB Connection Settings
    MONGO_TIMEOUT_MS: int = 5000
    MONGO_MAX_POOL_SIZE: int = 10
    MONGO_MIN_POOL_SIZE: int = 1

    # S3 / MinIO Configuration (object storage for question images)
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "question-images"
    S3_REGION: str = "us-east-1"
    S3_PRESIGN_EXPIRY_SECONDS: int = 3600

    @property
    def mongo_url(self) -> str:
        """
        Generate MongoDB connection URL with properly encoded credentials.

        URL encoding is critical for passwords with special characters.

        Returns:
            str: MongoDB connection string
        """
        # URL encode username and password to handle special characters
        encoded_user = quote_plus(self.MONGO_USER)
        encoded_password = quote_plus(self.MONGODB_PASSWORD)

        return (
            f"mongodb+srv://{encoded_user}:{encoded_password}"
            f"@{self.MONGO_CLUSTER}/?appName={self.MONGO_APPNAME}"
            f"&retryWrites=true&w=majority&authSource=admin"
        )

    @property
    def cors_origins(self) -> list:
        """
        Parse CORS origins from comma-separated string.

        Returns:
            list: List of allowed origins or ["*"] for all
        """
        if self.ALLOW_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOW_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Create global settings instance
settings = Settings()
