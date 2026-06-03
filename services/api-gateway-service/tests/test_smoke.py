"""Smoke / sanity tests for the API Gateway.

No DB or downstream services required. These exercise the pure routing
helpers, the X-User-* header injection, the public health endpoints, and the
auth boundary (a protected route with no credentials must 401).
"""
import main
import pytest
from fastapi.testclient import TestClient
from src.middleware.auth import add_user_context_headers

client = TestClient(main.app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_routes_endpoint_lists_configured_services():
    resp = client.get("/routes")
    assert resp.status_code == 200
    services = {r["service"] for r in resp.json()["routes"]}
    assert {"user-service", "test-management-service", "question-management-service"} <= services


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/v1/api/auth/login", "user-service"),
        ("/v1/api/users/5", "user-service"),
        ("/v1/api/tests", "test-management-service"),
        ("/v1/api/submissions/1", "test-management-service"),
        ("/v1/api/skills", "test-management-service"),
        ("/v1/api/questions", "question-management-service"),
    ],
)
def test_find_service_for_path(path, expected):
    assert main.find_service_for_path(path) == expected


def test_find_service_for_unknown_path_returns_none():
    assert main.find_service_for_path("/v1/api/nope") is None


def test_get_service_url_known_and_unknown():
    assert main.get_service_url("user-service") == "http://user-service:8002"
    with pytest.raises(ValueError):
        main.get_service_url("ghost-service")


def test_add_user_context_headers_stringifies():
    out = add_user_context_headers({}, {"user_id": 7, "email": "a@b.com", "role": "TRAINER"})
    assert out["X-User-Id"] == "7"
    assert out["X-User-Email"] == "a@b.com"
    assert out["X-User-Role"] == "TRAINER"


def test_add_user_context_headers_handles_missing_values():
    out = add_user_context_headers({}, {})
    assert out["X-User-Id"] == ""
    assert out["X-User-Email"] == ""
    assert out["X-User-Role"] == ""


def test_protected_route_without_credentials_is_401():
    resp = client.get("/v1/api/tests")
    assert resp.status_code == 401
