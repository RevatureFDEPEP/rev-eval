import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Settings are created during import, so test env vars must exist first.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "eval_ai_test")

# Ensure pytest can import main from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
