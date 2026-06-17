# src/config/settings.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- Shared database (read-only consumer of test-management's data) ----
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_NAME: str

    # ---- Service identity / runtime ----
    ALLOW_ORIGINS: str
    SERVICE_NAME: str
    LOG_LEVEL: str = "INFO"
    PORT: int = 8004
    SERVICE_HOSTNAME: str

    # NOTE: no JWT_SECRET. Role enforcement (W4-F3 require_trainer) reads the
    # X-User-Role header injected by the API gateway, which is the platform's
    # auth contract — downstream services never decode JWTs themselves.

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
