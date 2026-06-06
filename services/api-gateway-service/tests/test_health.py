import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure pytest can import main from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
