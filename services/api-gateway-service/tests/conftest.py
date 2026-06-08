import os

os.environ["JWT_SECRET"] = "test-gateway-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def valid_token():
    """Generate a valid JWT for testing authenticated routes."""
    payload = {
        "sub": "1",
        "email": "test@example.com",
        "role": "PARTICIPANT",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, "test-gateway-secret-key", algorithm="HS256")


@pytest.fixture(scope="module")
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}
