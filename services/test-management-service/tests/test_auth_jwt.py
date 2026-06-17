"""
Service-layer JWT auth tests for test-management-service.

Verifies that verify_jwt and require_role work correctly without a live
database — uses dependency_overrides to stub only what each test needs.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./tms_auth_test.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8002")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")
os.environ.setdefault("JWT_SECRET", "test-secret")

import time

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.utils.dependencies import require_role, verify_jwt

SECRET = "test-secret"


def _make_token(role: str = "TRAINER", expired: bool = False, secret: str = SECRET) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "42",
            "role": role,
            "email": "test@example.com",
            "exp": now - 10 if expired else now + 3600,
        },
        secret,
        algorithm="HS256",
    )


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ---------------------------------------------------------------------------
# verify_jwt unit tests — call the function directly, no HTTP needed
# ---------------------------------------------------------------------------

class TestVerifyJwt:
    def test_missing_token_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(None)
        assert exc_info.value.status_code == 401

    def test_invalid_token_returns_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(_creds("notavalidtoken"))
        assert exc_info.value.status_code == 401

    def test_expired_token_returns_401(self):
        token = _make_token(expired=True)
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(_creds(token))
        assert exc_info.value.status_code == 401

    def test_wrong_secret_returns_401(self):
        token = _make_token(secret="wrong-secret")
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(_creds(token))
        assert exc_info.value.status_code == 401

    def test_valid_trainer_token_returns_payload(self):
        from src.config.settings import settings as s
        import jwt as _jwt2
        import time as _t
        token = _jwt2.encode(
            {"sub": "1", "role": "TRAINER", "exp": int(_t.time()) + 3600},
            s.JWT_SECRET,
            algorithm="HS256",
        )
        payload = verify_jwt(_creds(token))
        assert payload["role"] == "TRAINER"


# ---------------------------------------------------------------------------
# require_role unit tests (isolated — override verify_jwt)
# ---------------------------------------------------------------------------

class TestRequireRole:
    def _trainer_payload(self) -> dict:
        return {"sub": "1", "role": "TRAINER", "exp": int(time.time()) + 3600}

    def _participant_payload(self) -> dict:
        return {"sub": "2", "role": "PARTICIPANT", "exp": int(time.time()) + 3600}

    def test_correct_role_passes(self):
        dep = require_role("TRAINER")
        result = dep(self._trainer_payload())
        assert result["role"] == "TRAINER"

    def test_wrong_role_raises_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep(self._participant_payload())
        assert exc_info.value.status_code == 403

    def test_missing_role_key_raises_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep({"sub": "1", "exp": int(time.time()) + 3600})
        assert exc_info.value.status_code == 403

    def test_case_insensitive_role_match(self):
        dep = require_role("trainer")
        result = dep({"sub": "1", "role": "TRAINER", "exp": int(time.time()) + 3600})
        assert result["role"] == "TRAINER"
