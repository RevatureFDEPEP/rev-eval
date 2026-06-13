import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from src.middleware import auth


class FakeResponse:
    def __init__(self, status_code=200, headers=None, json_data=None, content=b"ok"):
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/json"}
        self._json_data = json_data or {"ok": True}
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else str(content)

    def json(self):
        return self._json_data


class FakeAsyncClient:
    requests = []
    response = FakeResponse()
    error = None

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def request(self, method, url, **kwargs):
        FakeAsyncClient.requests.append((method, url, kwargs))
        if FakeAsyncClient.error:
            raise FakeAsyncClient.error
        return FakeAsyncClient.response


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


@pytest.fixture
def client(monkeypatch):
    FakeAsyncClient.requests = []
    FakeAsyncClient.response = FakeResponse()
    FakeAsyncClient.error = None
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)
    return TestClient(main.app)


def bearer(payload):
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_route_helpers_match_services_and_unknowns():
    assert main.find_service_for_path("/v1/api/auth/login") == "user-service"
    assert main.find_service_for_path("v1/api/questions") == "question-management-service"
    assert main.find_service_for_path("/v1/api/tests") == "test-management-service"
    assert main.find_service_for_path("/v1/api/nope") is None
    assert main.get_service_url("user-service") == "http://user-service:8002"

    with pytest.raises(ValueError):
        main.get_service_url("unknown-service")


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_missing_or_bad_headers():
    with pytest.raises(HTTPException) as missing:
        await auth.verify_jwt_token(None)
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as bad_format:
        await auth.verify_jwt_token("Token abc")
    assert bad_format.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_jwt_token_validates_secret_expiry_and_subject(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(HTTPException) as no_secret:
        auth._get_secret()
    assert no_secret.value.status_code == 500

    monkeypatch.setenv("JWT_SECRET", "test-secret")
    expired = jwt.encode(
        {"sub": "42", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        "test-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as expired_error:
        await auth.verify_jwt_token(f"Bearer {expired}")
    assert expired_error.value.detail == "Token expired"

    no_sub = jwt.encode({"email": "user@example.com"}, "test-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as missing_sub:
        await auth.verify_jwt_token(f"Bearer {no_sub}")
    assert "sub" in missing_sub.value.detail

    valid = jwt.encode(
        {"sub": "42", "email": "user@example.com", "role": "TRAINER"},
        "test-secret",
        algorithm="HS256",
    )
    context = await auth.verify_jwt_token(f"Bearer {valid}")
    assert context == {
        "user_id": "42",
        "email": "user@example.com",
        "role": "TRAINER",
    }


def test_add_user_context_headers_does_not_mutate_original():
    headers = {"Authorization": "Bearer token"}
    enriched = auth.add_user_context_headers(
        headers,
        {"user_id": "7", "email": "trainer@example.com", "role": "TRAINER"},
    )

    assert "X-User-Id" not in headers
    assert enriched["X-User-Id"] == "7"
    assert enriched["X-User-Email"] == "trainer@example.com"
    assert enriched["X-User-Role"] == "TRAINER"


def test_public_auth_proxy_forwards_query_and_json_response(client):
    response = client.post(
        "/v1/api/auth/login?next=/dashboard",
        json={"email": "user@example.com", "password": "Password123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    method, url, kwargs = FakeAsyncClient.requests[0]
    assert method == "POST"
    assert url == "http://user-service:8002/v1/api/auth/login?next=/dashboard"
    assert kwargs["content"]


def test_smart_gateway_forwards_with_user_context_headers(client):
    response = client.get(
        "/v1/api/tests?active=true",
        headers=bearer({"sub": "99", "email": "trainer@example.com", "role": "TRAINER"}),
    )

    assert response.status_code == 200
    method, url, kwargs = FakeAsyncClient.requests[0]
    assert method == "GET"
    assert url == "http://test-management-service:8001/v1/api/tests?active=true"
    assert kwargs["headers"]["X-User-Id"] == "99"


def test_smart_gateway_returns_404_for_unconfigured_path(client):
    response = client.get(
        "/v1/api/unknown",
        headers=bearer({"sub": "99"}),
    )

    assert response.status_code == 404
    assert "No service configured" in response.json()["detail"]


def test_smart_gateway_maps_connection_errors_to_503(client):
    FakeAsyncClient.error = httpx.ConnectError("offline")

    response = client.get(
        "/v1/api/questions",
        headers=bearer({"sub": "99"}),
    )

    assert response.status_code == 503
    assert "Cannot connect" in response.json()["detail"]


def test_routes_endpoint_lists_configured_patterns(client):
    response = client.get("/routes")

    assert response.status_code == 200
    assert any(route["service"] == "user-service" for route in response.json()["routes"])


def test_legacy_service_name_route_requires_auth(client):
    """The removed legacy route now falls through to the JWT-guarded smart
    route, so an unauthenticated /{service}/... request is rejected."""
    response = client.get("/user-service/v1/api/users/")

    assert response.status_code == 401
    # Request must never reach a downstream service.
    assert FakeAsyncClient.requests == []


def test_spoofed_user_role_is_replaced_with_verified_claim(client):
    response = client.get(
        "/v1/api/tests",
        headers={
            **bearer({"sub": "99", "email": "p@example.com", "role": "PARTICIPANT"}),
            "X-User-Role": "ADMIN",
            "X-User-Id": "1",
        },
    )

    assert response.status_code == 200
    _, _, kwargs = FakeAsyncClient.requests[0]
    forwarded = kwargs["headers"]
    # Forwarded identity comes from the verified token, not the spoofed header.
    assert forwarded["X-User-Role"] == "PARTICIPANT"
    assert forwarded["X-User-Id"] == "99"
    # No lowercase spoofed copy survives.
    assert "x-user-role" not in forwarded


def test_spoofed_internal_key_is_stripped(client):
    response = client.get(
        "/v1/api/tests",
        headers={
            **bearer({"sub": "99", "email": "p@example.com", "role": "TRAINER"}),
            "X-Internal-Key": "attacker-supplied",
        },
    )

    assert response.status_code == 200
    _, _, kwargs = FakeAsyncClient.requests[0]
    forwarded = {k.lower(): v for k, v in kwargs["headers"].items()}
    assert "x-internal-key" not in forwarded
