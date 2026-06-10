# src/config/settings.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str
    MONGO_USER: str | None = None  # Optional - service uses PostgreSQL only
    MONGODB_PASSWORD: str | None = None  # Optional - service uses PostgreSQL only
    ALLOW_ORIGINS: str
    SERVICE_NAME: str
    LOG_LEVEL: str = "INFO"
    PORT: int
    SERVICE_HOSTNAME: str

    # Service-to-Service Communication
    USER_SERVICE_URL: str = "http://localhost:8003"
    INTERVIEW_SERVICE_URL: str | None = (
        None  # not yet implemented; None = skip interview calls
    )
    QUESTION_MANAGEMENT_SERVICE_URL: str = "http://localhost:8003"

    # Quiz sessions
    DEFAULT_QUIZ_DURATION_MINUTES: int = 30  # fallback when a test has no duration

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
