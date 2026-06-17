from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from main import find_service_for_path, get_service_url
from src.middleware.auth import add_user_context_headers

# ===== HEALTH AND ROUTES =====


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_routes(client):
    response = client.get("/routes")
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert isinstance(data["routes"], list)
    assert len(data["routes"]) == 8


# ===== find_service_for_path =====


def test_find_service_auth():
    assert find_service_for_path("/v1/api/auth/login") == "user-service"


def test_find_service_users():
    assert find_service_for_path("/v1/api/users/1") == "user-service"


def test_find_service_tests():
    assert find_service_for_path("/v1/api/tests/") == "test-management-service"


def test_find_service_test_sessions():
    assert find_service_for_path("/v1/api/test-sessions/") == "test-management-service"


def test_find_service_test_sessions_bare():
    assert find_service_for_path("/v1/api/test-sessions") == "test-management-service"


def test_find_service_questions():
    assert find_service_for_path("/v1/api/questions/") == "question-management-service"


def test_find_service_skills():
    assert find_service_for_path("/v1/api/skills/") == "test-management-service"


def test_find_service_submissions():
    assert find_service_for_path("/v1/api/submissions/") == "test-management-service"


def test_find_service_unknown():
    assert find_service_for_path("/v1/api/unknown/") is None


# ===== get_service_url =====


def test_get_service_url_user():
    assert get_service_url("user-service") == "http://user-service:8002"


def test_get_service_url_test_mgmt():
    assert (
        get_service_url("test-management-service")
        == "http://test-management-service:8001"
    )


def test_get_service_url_unknown():
    with pytest.raises(ValueError):
        get_service_url("nonexistent")


# ===== add_user_context_headers =====


def test_add_user_context_headers():
    user_context = {"user_id": "1", "email": "a@b.com", "role": "TRAINER"}
    result = add_user_context_headers({}, user_context)
    assert result["X-User-Id"] == "1"
    assert result["X-User-Email"] == "a@b.com"
    assert result["X-User-Role"] == "TRAINER"


def test_add_user_context_headers_does_not_mutate_original():
    original = {"existing-header": "value"}
    user_context = {"user_id": "2", "email": "b@c.com", "role": "PARTICIPANT"}
    add_user_context_headers(original, user_context)
    assert "X-User-Id" not in original
    assert "X-User-Email" not in original
    assert "X-User-Role" not in original
    assert original == {"existing-header": "value"}


# ===== smart_gateway (JWT-protected routes) =====


def test_smart_gateway_no_auth_header(client):
    response = client.get("/v1/api/tests/")
    assert response.status_code == 401


def test_smart_gateway_invalid_token(client):
    response = client.get(
        "/v1/api/tests/", headers={"Authorization": "Bearer badtoken"}
    )
    assert response.status_code == 401


def test_smart_gateway_valid_token_proxies(client, auth_headers):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"data": "ok"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/tests/", headers=auth_headers)

    assert response.status_code == 200


def test_smart_gateway_no_matching_service(client, auth_headers):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"data": "ok"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/unknownpath", headers=auth_headers)

    assert response.status_code == 404


# ===== public_auth_proxy =====


def _make_mock_client(
    status_code: int, content_type: str = "application/json", body=None
):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.headers = {"content-type": content_type}
    mock_response.json.return_value = body or {}
    mock_response.content = b"{}"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)
    return mock_client


def test_public_auth_login_proxy(client):
    mock_client = _make_mock_client(200, body={"token": "abc"})
    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.post(
            "/v1/api/auth/login", json={"email": "a@b.com", "password": "pass"}
        )
    assert response.status_code == 200


def test_public_auth_register_proxy(client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"id": "1"}
    mock_response.content = b'{"id": "1"}'

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.post(
            "/v1/api/auth/register",
            json={"email": "new@example.com", "password": "pass", "name": "Test User"},
        )
    assert response.status_code == 201


def test_public_auth_proxy_with_query_params(client):
    """Covers main.py:131 — query string appended to target_url."""
    mock_client = _make_mock_client(200, body={"ok": True})
    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/auth/me?foo=bar")
    assert response.status_code == 200


def test_public_auth_proxy_non_json_response(client):
    """Covers main.py:149 — non-JSON content-type returned by upstream."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.content = b"plain text"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/auth/something")
    assert response.status_code == 200


# ===== smart_gateway additional coverage =====


def test_smart_gateway_with_query_params(client, auth_headers):
    """Covers main.py:192 — query string forwarded in smart_gateway."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = []

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/tests/?page=1&limit=10", headers=auth_headers)
    assert response.status_code == 200


def test_smart_gateway_4xx_response_logging(client, auth_headers):
    """Covers main.py:223-227 — error response logging branch (status >= 400)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"detail": "not found"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/tests/9999", headers=auth_headers)
    assert response.status_code == 404


def test_smart_gateway_non_json_upstream_response(client, auth_headers):
    """Covers main.py:235-239 — non-JSON content-type from upstream in smart_gateway."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.content = b"raw bytes"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        response = client.get("/v1/api/tests/export", headers=auth_headers)
    assert response.status_code == 200


def test_smart_gateway_connect_error(client, auth_headers):
    """Covers main.py:243-248 — httpx.ConnectError raises 503."""
    import httpx as httpx_lib

    with patch("main.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(side_effect=httpx_lib.ConnectError("refused"))
        mock_cls.return_value = mock_instance

        response = client.get("/v1/api/tests/", headers=auth_headers)
    assert response.status_code == 503


def test_smart_gateway_generic_exception(client, auth_headers):
    """Covers main.py:249-254 — generic Exception raises 500."""
    with patch("main.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.request = AsyncMock(side_effect=RuntimeError("boom"))
        mock_cls.return_value = mock_instance

        response = client.get("/v1/api/tests/", headers=auth_headers)
    assert response.status_code == 500


# ===== middleware/auth.py additional coverage =====


def test_verify_jwt_malformed_auth_header(client):
    """Covers auth.py:39 — auth header not in 'Bearer token' format."""
    response = client.get("/v1/api/tests/", headers={"Authorization": "NotBearer"})
    assert response.status_code == 401


def test_verify_jwt_expired_token(client):
    """Covers auth.py:51 — expired token raises 401."""
    expired = jwt.encode(
        {"sub": "1", "email": "x@y.com", "exp": datetime(2020, 1, 1, tzinfo=UTC)},
        "test-gateway-secret-key",
        algorithm="HS256",
    )
    response = client.get(
        "/v1/api/tests/", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_verify_jwt_missing_sub_claim(client):
    """Covers auth.py:65 — valid JWT but no 'sub' claim raises 401."""
    no_sub = jwt.encode(
        {
            "email": "x@y.com",
            "role": "PARTICIPANT",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "test-gateway-secret-key",
        algorithm="HS256",
    )
    response = client.get(
        "/v1/api/tests/", headers={"Authorization": f"Bearer {no_sub}"}
    )
    assert response.status_code == 401


def test_get_secret_missing_env(monkeypatch):
    """Covers auth.py:21 — JWT_SECRET not set raises HTTPException 500."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    from fastapi import HTTPException
    from src.middleware.auth import _get_secret

    with pytest.raises(HTTPException) as exc_info:
        _get_secret()
    assert exc_info.value.status_code == 500
