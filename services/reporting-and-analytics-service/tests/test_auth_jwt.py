"""
Service-layer JWT auth tests for reporting-and-analytics-service.

These tests run WITHOUT the module-level dependency_overrides in test_reports.py.
They use a fresh TestClient per test so overrides don't bleed across.
"""
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./reporting_test.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "reporting-and-analytics-service")

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.utils.dependencies import require_role, verify_jwt

SECRET = "test-secret"


def _make_token(role: str = "TRAINER", expired: bool = False, secret: str = SECRET) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "99",
            "role": role,
            "email": "trainer@example.com",
            "exp": now - 10 if expired else now + 3600,
        },
        secret,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# require_role factory — pure unit tests (no DB, no HTTP)
# ---------------------------------------------------------------------------

class TestRequireRole:
    def _payload(self, role: str) -> dict:
        return {"sub": "1", "role": role, "exp": int(time.time()) + 3600}

    def test_trainer_payload_passes(self):
        dep = require_role("TRAINER")
        result = dep(self._payload("TRAINER"))
        assert result["role"] == "TRAINER"

    def test_participant_payload_raises_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep(self._payload("PARTICIPANT"))
        assert exc_info.value.status_code == 403

    def test_empty_role_raises_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep({"sub": "1", "role": "", "exp": int(time.time()) + 3600})
        assert exc_info.value.status_code == 403

    def test_missing_role_key_raises_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep({"sub": "1", "exp": int(time.time()) + 3600})
        assert exc_info.value.status_code == 403

    def test_case_insensitive_match(self):
        dep = require_role("trainer")
        result = dep(self._payload("TRAINER"))
        assert result["role"] == "TRAINER"

    def test_participant_role_can_access_participant_dep(self):
        dep = require_role("PARTICIPANT")
        result = dep(self._payload("PARTICIPANT"))
        assert result["role"] == "PARTICIPANT"


# ---------------------------------------------------------------------------
# HTTP-level: verify 401 when no token / wrong token on protected endpoints
# ---------------------------------------------------------------------------

class TestEndpointAuth:
    def setup_method(self):
        from src.config import settings as cfg
        cfg.settings.JWT_SECRET = SECRET
        # Remove any existing overrides so JWT path is exercised
        from main import app
        from src.utils.dependencies import get_current_trainer, get_current_user
        app.dependency_overrides.pop(get_current_trainer, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(verify_jwt, None)

    def teardown_method(self):
        # Restore trainer override so other test modules still work
        from main import app
        from src.utils.dependencies import get_current_trainer, get_current_user
        app.dependency_overrides.pop(get_current_trainer, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(verify_jwt, None)

    def test_aggregate_no_token_returns_401(self):
        from main import app
        with TestClient(app) as client:
            resp = client.get("/v1/api/reports/aggregate")
        assert resp.status_code == 401

    def test_aggregate_invalid_token_returns_401(self):
        from main import app
        with TestClient(app) as client:
            resp = client.get(
                "/v1/api/reports/aggregate",
                headers={"Authorization": "Bearer notvalid"},
            )
        assert resp.status_code == 401

    def test_aggregate_expired_token_returns_401(self):
        from main import app
        token = _make_token(expired=True)
        with TestClient(app) as client:
            resp = client.get(
                "/v1/api/reports/aggregate",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 401

    def test_aggregate_participant_token_returns_403(self):
        from main import app
        token = _make_token(role="PARTICIPANT")
        with TestClient(app) as client:
            resp = client.get(
                "/v1/api/reports/aggregate",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_rankings_no_token_returns_401(self):
        from main import app
        with TestClient(app) as client:
            resp = client.get("/v1/api/reports/tests/1/rankings")
        assert resp.status_code == 401

    def test_rankings_participant_token_returns_403(self):
        from main import app
        token = _make_token(role="PARTICIPANT")
        with TestClient(app) as client:
            resp = client.get(
                "/v1/api/reports/tests/1/rankings",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
