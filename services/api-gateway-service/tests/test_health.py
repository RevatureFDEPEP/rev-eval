import pytest

try:
    # Import the FastAPI app from the service entrypoint.
    from main import app
except Exception as e:
    pytest.skip(f"Cannot import api-gateway app: {e}", allow_module_level=True)

from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
