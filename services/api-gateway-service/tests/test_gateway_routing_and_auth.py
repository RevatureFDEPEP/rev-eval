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


TEST_SECRET = "unit-test-secret-key-that-is-long-enough-1234567890"
TEST_ISSUER = "rev-eval-user-service"
TEST_AUDIENCE = "rev-eval-clients"


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("JWT_AUDIENCE", TEST_AUDIENCE)


@pytest.fixture
def client(monkeypatch):
    FakeAsyncClient.requests = []
    FakeAsyncClient.response = FakeResponse()
    FakeAsyncClient.error = None
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)
    return TestClient(main.app)


def _claims(**overrides):
    """Build a fully-claimed token payload; overrides win."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "99",
        "email": "user@example.com",
        "role": "TRAINER",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
    }
    payload.update(overrides)
    return payload


def bearer(payload):
    """Bearer header for a token, filling in required claims when omitted."""
    token = jwt.encode(_claims(**payload), TEST_SECRET, algorithm="HS256")
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


def _token(**overrides):
    return jwt.encode(_claims(**overrides), TEST_SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_get_secret_raises_500_when_unset(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(HTTPException) as no_secret:
        auth._get_secret()
    assert no_secret.value.status_code == 500


@pytest.mark.asyncio
async def test_verify_jwt_token_accepts_fully_claimed_token():
    context = await auth.verify_jwt_token(f"Bearer {_token(sub='42', role='TRAINER')}")
    assert context == {
        "user_id": "42",
        "email": "user@example.com",
        "role": "TRAINER",
    }


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_expired():
    now = datetime.now(timezone.utc)
    expired = _token(exp=now - timedelta(minutes=1), nbf=now - timedelta(minutes=5),
                     iat=now - timedelta(minutes=5))
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {expired}")
    assert err.value.detail == "Token expired"


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_future_nbf():
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {_token(nbf=future, iat=future)}")
    assert err.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_wrong_issuer():
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {_token(iss='evil-issuer')}")
    assert err.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_wrong_audience():
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {_token(aud='some-other-aud')}")
    assert err.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_missing_role():
    payload = _claims(sub="42")
    payload.pop("role")
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {token}")
    assert err.value.status_code == 401
    assert "role" in err.value.detail


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_unknown_role():
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {_token(role='SUPERUSER')}")
    assert err.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_jwt_token_rejects_missing_required_claim():
    # A token with no exp/iat/nbf/iss/aud must be rejected.
    bare = jwt.encode({"sub": "42", "role": "TRAINER"}, TEST_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as err:
        await auth.verify_jwt_token(f"Bearer {bare}")
    assert err.value.status_code == 401


@pytest.mark.asyncio
async def test_validate_jwt_secret_rejects_default_and_short(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    monkeypatch.delenv("ALLOW_INSECURE_DEV_SECRETS", raising=False)
    with pytest.raises(RuntimeError):
        auth.validate_jwt_secret()

    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(RuntimeError):
        auth.validate_jwt_secret()

    # Escape hatch allows weak secrets for local dev.
    monkeypatch.setenv("ALLOW_INSECURE_DEV_SECRETS", "true")
    auth.validate_jwt_secret()

    # A strong secret passes regardless of the escape hatch.
    monkeypatch.delenv("ALLOW_INSECURE_DEV_SECRETS", raising=False)
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    auth.validate_jwt_secret()


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


# ===== Phase 3: empty-body / non-JSON passthrough =====

def test_relay_204_returns_204_not_500():
    resp = FakeResponse(204, headers={"content-type": "application/json"}, content=b"")
    relayed = main.relay_downstream_response(resp)
    assert relayed.status_code == 204
    assert relayed.body == b""


def test_relay_empty_body_is_not_json_decoded():
    # Empty body with a JSON content-type must not be decoded (would raise).
    resp = FakeResponse(200, headers={"content-type": "application/json"}, content=b"")
    relayed = main.relay_downstream_response(resp)
    assert relayed.status_code == 200
    assert relayed.body == b""


def test_relay_non_json_body_unchanged():
    resp = FakeResponse(200, headers={"content-type": "text/plain"}, content=b"plain text")
    relayed = main.relay_downstream_response(resp)
    assert relayed.status_code == 200
    assert relayed.body == b"plain text"
    assert relayed.media_type == "text/plain"


def test_relay_json_body_preserved():
    resp = FakeResponse(200, headers={"content-type": "application/json"}, json_data={"a": 1}, content=b'{"a": 1}')
    relayed = main.relay_downstream_response(resp)
    assert relayed.status_code == 200
    assert relayed.body == b'{"a":1}'


def test_smart_gateway_delete_204_passthrough(client):
    FakeAsyncClient.response = FakeResponse(
        204, headers={"content-type": "application/json"}, content=b""
    )
    response = client.delete(
        "/v1/api/submissions/5/",
        headers=bearer({"sub": "1", "role": "TRAINER"}),
    )
    assert response.status_code == 204
    assert response.content == b""


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
