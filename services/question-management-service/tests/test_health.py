import os

from fastapi.testclient import TestClient

# Settings are created during import, so test env vars must exist first.
os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("PORT", "8003")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/evalai")
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3000")

from main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
