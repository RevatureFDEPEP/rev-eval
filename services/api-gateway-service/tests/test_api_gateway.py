"""Tests for api-gateway-service JWT middleware and utility functions."""
import asyncio
import os
import time

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch

# Set required env vars before importing app modules
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci-tests")
os.environ.setdefault("SERVICE_NAME", "api-gateway-service")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3000")

from main import app, find_service_for_path, get_service_url
from src.middleware.auth import _get_secret, add_user_context_headers, verify_jwt_token

TEST_SECRET = os.environ["JWT_SECRET"]
client = TestClient(app, raise_server_exceptions=False)


def make_token(payload: dict, secret: str = TEST_SECRET) -> str:
    return pyjwt.encode(payload, secret, algorithm="HS256")


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _get_secret
# ---------------------------------------------------------------------------

class TestGetSecret:
    def test_returns_value_when_set(self):
        with patch.dict(os.environ, {"JWT_SECRET": "my-secret"}):
            assert _get_secret() == "my-secret"

    def test_raises_500_when_missing(self):
        env_without = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
        with patch.dict(os.environ, env_without, clear=True):
            with pytest.raises(HTTPException) as exc:
                _get_secret()
        assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# add_user_context_headers
# ---------------------------------------------------------------------------

class TestAddUserContextHeaders:
    def test_injects_x_user_headers(self):
        result = add_user_context_headers(
            {"content-type": "application/json"},
            {"user_id": "7", "email": "bob@test.com", "role": "TRAINER"},
        )
        assert result["X-User-Id"] == "7"
        assert result["X-User-Email"] == "bob@test.com"
        assert result["X-User-Role"] == "TRAINER"
        assert result["content-type"] == "application/json"

    def test_does_not_mutate_original_dict(self):
        original = {"a": "1"}
        add_user_context_headers(original, {"user_id": "1", "email": "", "role": ""})
        assert "X-User-Id" not in original

    def test_returns_new_dict(self):
        original = {}
        result = add_user_context_headers(original, {"user_id": "1", "email": "", "role": ""})
        assert result is not original

    def test_empty_context_produces_empty_strings(self):
        result = add_user_context_headers({}, {})
        assert result["X-User-Id"] == ""
        assert result["X-User-Email"] == ""
        assert result["X-User-Role"] == ""

    def test_numeric_user_id_coerced_to_string(self):
        result = add_user_context_headers({}, {"user_id": 42, "email": "", "role": ""})
        assert result["X-User-Id"] == "42"


# ---------------------------------------------------------------------------
# verify_jwt_token (async FastAPI dependency, called directly)
# ---------------------------------------------------------------------------

class TestVerifyJwtToken:
    def test_missing_header_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization=None))
        assert exc.value.status_code == 401

    def test_single_word_header_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization="justoneword"))
        assert exc.value.status_code == 401

    def test_non_bearer_scheme_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization="Basic abc123"))
        assert exc.value.status_code == 401

    def test_expired_token_raises_401(self):
        token = make_token({"sub": "1", "exp": int(time.time()) - 3600})
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization=f"Bearer {token}"))
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()

    def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization="Bearer not.a.valid.jwt.token"))
        assert exc.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        token = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization=f"Bearer {token}"))
        assert exc.value.status_code == 401

    def test_missing_sub_claim_raises_401(self):
        token = make_token({"email": "x@test.com", "role": "TRAINER"})
        with pytest.raises(HTTPException) as exc:
            run(verify_jwt_token(authorization=f"Bearer {token}"))
        assert exc.value.status_code == 401
        assert "sub" in exc.value.detail.lower()

    def test_valid_token_returns_user_context(self):
        token = make_token({"sub": "42", "email": "alice@test.com", "role": "TRAINER"})
        result = run(verify_jwt_token(authorization=f"Bearer {token}"))
        assert result["user_id"] == "42"
        assert result["email"] == "alice@test.com"
        assert result["role"] == "TRAINER"

    def test_valid_token_optional_claims_default_empty(self):
        token = make_token({"sub": "99"})
        result = run(verify_jwt_token(authorization=f"Bearer {token}"))
        assert result["user_id"] == "99"
        assert result["email"] == ""
        assert result["role"] == ""


# ---------------------------------------------------------------------------
# App endpoints
# ---------------------------------------------------------------------------

class TestAppEndpoints:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_routes_returns_route_list(self):
        resp = client.get("/routes")
        assert resp.status_code == 200
        data = resp.json()
        assert "routes" in data
        assert len(data["routes"]) > 0
        assert any(r["service"] == "user-service" for r in data["routes"])
        assert any(r["service"] == "test-management-service" for r in data["routes"])


# ---------------------------------------------------------------------------
# find_service_for_path
# ---------------------------------------------------------------------------

class TestFindServiceForPath:
    def test_auth_path(self):
        assert find_service_for_path("/v1/api/auth/login") == "user-service"

    def test_users_path(self):
        assert find_service_for_path("/v1/api/users/profile") == "user-service"

    def test_tests_path(self):
        assert find_service_for_path("/v1/api/tests") == "test-management-service"

    def test_submissions_path(self):
        assert find_service_for_path("/v1/api/submissions/123") == "test-management-service"

    def test_dashboard_path(self):
        assert find_service_for_path("/v1/api/dashboard") == "test-management-service"

    def test_skills_path(self):
        assert find_service_for_path("/v1/api/skills") == "test-management-service"

    def test_questions_path(self):
        assert find_service_for_path("/v1/api/questions") == "question-management-service"

    def test_unknown_path_returns_none(self):
        assert find_service_for_path("/v1/api/nonexistent") is None

    def test_path_without_leading_slash_still_resolves(self):
        assert find_service_for_path("v1/api/tests") == "test-management-service"


# ---------------------------------------------------------------------------
# get_service_url
# ---------------------------------------------------------------------------

class TestGetServiceUrl:
    def test_user_service_url(self):
        assert get_service_url("user-service") == "http://user-service:8002"

    def test_test_management_url(self):
        assert get_service_url("test-management-service") == "http://test-management-service:8001"

    def test_question_management_url(self):
        assert get_service_url("question-management-service") == "http://question-management-service:8003"

    def test_unknown_service_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown service"):
            get_service_url("imaginary-service")
