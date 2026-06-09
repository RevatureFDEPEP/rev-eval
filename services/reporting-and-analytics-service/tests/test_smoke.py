"""Smoke / sanity tests for reporting-and-analytics-service.

No DB required. These cover settings loading, the async DB URL construction,
and the /health endpoint — enough to keep the CI coverage gate honest while the
service is a scaffold (business endpoints land in W4-F1).
"""
from fastapi.testclient import TestClient
from main import app
from src.config.settings import settings


def test_settings_async_db_url():
    assert settings.SQLALCHEMY_DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.DB_NAME in settings.SQLALCHEMY_DATABASE_URL


def test_service_name_default():
    assert settings.SERVICE_NAME == "reporting-and-analytics-service"
    assert settings.PORT == 8004


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
