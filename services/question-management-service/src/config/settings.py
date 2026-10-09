# src/config/settings.py
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus

# The value .env.example and docker-compose.yml use for local development. It is
# accepted only when APP_ENV=development.
DEV_INTERNAL_SERVICE_TOKEN = "change-me-internal-service-token"


def internal_token_allowed(token: Optional[str], app_env: str) -> bool:
    token = (token or "").strip()
    if not token:
        return False
    return token != DEV_INTERNAL_SERVICE_TOKEN or app_env.strip().lower() == "development"



class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    MongoDB connection prefers MONGO_URI (direct, used for local docker-compose
    or any non-Atlas deployment); falls back to assembling a `mongodb+srv://`
    URL from MONGO_USER + MONGODB_PASSWORD + MONGO_CLUSTER for Atlas use.
    """
    # MongoDB Configuration
    MONGO_URI: Optional[str] = None  # If set, used directly (e.g. mongodb://mongo:27017/evalai)
    MONGO_USER: Optional[str] = None
    MONGODB_PASSWORD: Optional[str] = None
    MONGO_CLUSTER: Optional[str] = None
    MONGO_APPNAME: str = "EvalAI"
    MONGO_DB: str = "evalai"

    JWT_SECRET: str = "change-me-in-production"

    # Shared secret that test-management-service sends in X-Internal-Service-Token
    # to read the question bank, answer keys included, for scoring. Unset or
    # empty: no caller is treated as internal.
    INTERNAL_SERVICE_TOKEN: Optional[str] = None

    # "development" allows the placeholder internal token; anything else
    # refuses to start with it.
    APP_ENV: str = "production"

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
    # Origin the *browser* uses to reach object storage. Presigned URLs are
    # signed for this host (SigV4 covers the Host header), so it must be the
    # address the client actually requests, e.g. the Nginx edge that proxies
    # the bucket path to MinIO. Unset: presign against S3_ENDPOINT_URL.
    S3_PUBLIC_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "question-images"
    S3_REGION: str = "us-east-1"
    S3_PRESIGN_EXPIRY_SECONDS: int = 3600

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
    def mongo_url(self) -> str:
        """
        Return the MongoDB connection URL.

        Prefers MONGO_URI when set (local docker-compose or self-hosted).
        Otherwise assembles a `mongodb+srv://` URL from individual components
        (Atlas-style).
        """
        if self.MONGO_URI:
            return self.MONGO_URI

        if not (self.MONGO_USER and self.MONGODB_PASSWORD and self.MONGO_CLUSTER):
            raise ValueError(
                "MongoDB connection not configured: set MONGO_URI, "
                "or MONGO_USER + MONGODB_PASSWORD + MONGO_CLUSTER",
            )

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
