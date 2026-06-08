"""Routing-table + auth-boundary tests for the API Gateway.

No downstream services required. These parametrize the full ROUTES regex table
(every configured pattern → service), exercise the X-User-* header injection,
and assert the auth boundary: protected routes 401 without a token while the
public /v1/api/auth/* pass-through skips JWT verification entirely.
"""
import main
import pytest
from fastapi.testclient import TestClient
from src.middleware.auth import add_user_context_headers

# raise_server_exceptions=False so the public-auth pass-through (which tries to
# reach user-service and fails in a hermetic run) surfaces as a 5xx response
# rather than raising — we only care that it is NOT a 401.
client = TestClient(main.app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path, expected_service",
    [
        ("/v1/api/auth/login", "user-service"),
        ("/v1/api/auth/register", "user-service"),
        ("/v1/api/users", "user-service"),
        ("/v1/api/users/42", "user-service"),
        ("/v1/api/dashboard", "test-management-service"),
        ("/v1/api/dashboard/trainer", "test-management-service"),
        ("/v1/api/tests", "test-management-service"),
        ("/v1/api/tests/5/submissions", "test-management-service"),
        ("/v1/api/submissions", "test-management-service"),
        ("/v1/api/submissions/9", "test-management-service"),
        ("/v1/api/skills", "test-management-service"),
        ("/v1/api/categories", "test-management-service"),
        ("/v1/api/categories/1/skills", "test-management-service"),
        ("/v1/api/questions", "question-management-service"),
        ("/v1/api/questions/abc123", "question-management-service"),
    ],
)
def test_every_route_pattern_maps_to_its_service(path, expected_service):
    assert main.find_service_for_path(path) == expected_service


def test_routes_table_has_an_entry_per_known_service():
    services = {r["service"] for r in main.ROUTES}
    assert services == {
        "user-service",
        "test-management-service",
        "question-management-service",
    }


@pytest.mark.parametrize(
    "path",
    ["/v1/api/nope", "/random", "/v2/api/tests", "/v1/api"],
)
def test_unmatched_paths_return_none(path):
    assert main.find_service_for_path(path) is None


def test_get_service_url_resolves_known_ports():
    assert main.get_service_url("user-service") == "http://user-service:8002"
    assert main.get_service_url("test-management-service") == "http://test-management-service:8001"
    assert main.get_service_url("question-management-service") == "http://question-management-service:8003"


def test_get_service_url_unknown_raises():
    with pytest.raises(ValueError):
        main.get_service_url("nope")


@pytest.mark.parametrize(
    "context, expected",
    [
        ({"user_id": 7, "email": "a@b.com", "role": "TRAINER"},
         {"X-User-Id": "7", "X-User-Email": "a@b.com", "X-User-Role": "TRAINER"}),
        ({}, {"X-User-Id": "", "X-User-Email": "", "X-User-Role": ""}),
    ],
)
def test_user_context_headers_injected(context, expected):
    out = add_user_context_headers({}, context)
    for key, value in expected.items():
        assert out[key] == value


@pytest.mark.parametrize(
    "path",
    ["/v1/api/tests", "/v1/api/users/1", "/v1/api/questions", "/v1/api/submissions"],
)
def test_protected_routes_require_a_token(path):
    """Smart-routed endpoints sit behind verify_jwt_token — no token => 401."""
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", list(main.PUBLIC_PATH_PREFIXES))
def test_public_auth_paths_skip_jwt(path):
    """login/register bypass JWT — they must NOT 401 (they reach the proxy and
    fail to connect downstream in a hermetic run, which is a 5xx, not a 401)."""
    resp = client.post(path, json={})
    assert resp.status_code != 401
