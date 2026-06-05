import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, find_service_for_path, get_service_url

from src.middleware.auth import add_user_context_headers, verify_jwt_token

client = TestClient(app)


# --- find_service_for_path ---


def test_route_auth_path():
    assert find_service_for_path("/v1/api/auth/login") == "user-service"


def test_route_users_path():
    assert find_service_for_path("/v1/api/users/1") == "user-service"


def test_route_tests_path():
    assert find_service_for_path("/v1/api/tests/5") == "test-management-service"


def test_route_submissions_path():
    assert find_service_for_path("/v1/api/submissions") == "test-management-service"


def test_route_skills_path():
    assert find_service_for_path("/v1/api/skills") == "test-management-service"


def test_route_questions_path():
    assert find_service_for_path("/v1/api/questions") == "question-management-service"


def test_route_unknown_path():
    assert find_service_for_path("/v1/api/unknown") is None


# --- get_service_url ---


def test_get_service_url_user():
    assert get_service_url("user-service") == "http://user-service:8002"


def test_get_service_url_test_management():
    assert (
        get_service_url("test-management-service")
        == "http://test-management-service:8001"
    )


def test_get_service_url_question_management():
    assert (
        get_service_url("question-management-service")
        == "http://question-management-service:8003"
    )


def test_get_service_url_unknown_raises():
    with pytest.raises(ValueError, match="Unknown service"):
        get_service_url("nonexistent-service")


# --- add_user_context_headers ---


def test_header_injection_all_fields():
    context = {"user_id": "42", "email": "alice@example.com", "role": "TRAINER"}
    result = add_user_context_headers({}, context)
    assert result["X-User-Id"] == "42"
    assert result["X-User-Email"] == "alice@example.com"
    assert result["X-User-Role"] == "TRAINER"


def test_header_injection_preserves_existing():
    existing = {"Content-Type": "application/json"}
    result = add_user_context_headers(
        existing, {"user_id": "1", "email": "", "role": ""}
    )
    assert result["Content-Type"] == "application/json"
    assert result["X-User-Id"] == "1"


def test_header_injection_does_not_mutate_original():
    original = {"Authorization": "Bearer token"}
    add_user_context_headers(original, {"user_id": "1", "email": "", "role": ""})
    assert "X-User-Id" not in original


# --- HTTP endpoints ---


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_routes_endpoint_lists_patterns():
    resp = client.get("/routes")
    assert resp.status_code == 200
    data = resp.json()
    assert "routes" in data
    patterns = [r["pattern"] for r in data["routes"]]
    assert any("tests" in p for p in patterns)


def test_protected_route_no_auth_returns_401():
    resp = client.get("/v1/api/tests")
    assert resp.status_code == 401


# --- verify_jwt_token (called directly, no FastAPI DI needed) ---


def _make_token(
    payload: dict,
    secret: str = "test-secret-key-for-gateway-tests-only",
    expired: bool = False,
) -> str:
    if expired:
        payload["exp"] = 0
    return pyjwt.encode(payload, secret, algorithm="HS256")


def test_verify_jwt_valid_token():
    token = _make_token({"sub": "42", "email": "alice@example.com", "role": "TRAINER"})
    result = asyncio.run(verify_jwt_token(f"Bearer {token}"))
    assert result["user_id"] == "42"
    assert result["email"] == "alice@example.com"
    assert result["role"] == "TRAINER"


def test_verify_jwt_malformed_bearer():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_jwt_token("notbearer token extra"))
    assert exc.value.status_code == 401


def test_verify_jwt_expired_token():
    token = _make_token({"sub": "1"}, expired=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_jwt_token(f"Bearer {token}"))
    assert exc.value.status_code == 401


def test_verify_jwt_invalid_signature():
    token = _make_token({"sub": "1"}, secret="wrong-secret")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_jwt_token(f"Bearer {token}"))
    assert exc.value.status_code == 401


def test_verify_jwt_missing_sub_claim():
    token = _make_token({"email": "a@b.com", "role": "PARTICIPANT"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_jwt_token(f"Bearer {token}"))
    assert exc.value.status_code == 401


# --- Route handler tests (httpx mocked — no network) ---


def _mock_httpx(status: int = 200, body: dict | None = None):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = body or {}
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.content = b"{}"

    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value=mock_resp)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def test_public_auth_proxy_forwards_login():
    with patch(
        "httpx.AsyncClient", return_value=_mock_httpx(200, {"access_token": "tok"})
    ):
        resp = client.post(
            "/v1/api/auth/login", json={"email": "t@t.com", "password": "pass"}
        )
    assert resp.status_code == 200


def test_smart_gateway_forwards_with_valid_jwt():
    token = _make_token({"sub": "42", "email": "a@b.com", "role": "TRAINER"})
    with patch("httpx.AsyncClient", return_value=_mock_httpx(200, {"tests": []})):
        resp = client.get("/v1/api/tests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
