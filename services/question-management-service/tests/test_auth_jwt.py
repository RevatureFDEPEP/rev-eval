"""
Service-layer JWT auth tests for question-management-service.

Tests verify_jwt and require_role without MongoDB — stubs out Beanie
via dependency_overrides so the focus is purely on auth logic.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("JWT_SECRET", "test-secret")

import time

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from src.utils.dependencies import require_role, verify_jwt

SECRET = "test-secret"


def _make_token(role: str = "TRAINER", expired: bool = False, secret: str = SECRET) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "42",
            "role": role,
            "email": "trainer@example.com",
            "exp": now - 10 if expired else now + 3600,
        },
        secret,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# require_role factory — pure unit tests (no HTTP)
# ---------------------------------------------------------------------------

class TestRequireRole:
    def _payload(self, role: str) -> dict:
        return {"sub": "1", "role": role, "exp": int(time.time()) + 3600}

    def test_trainer_passes(self):
        dep = require_role("TRAINER")
        result = dep(self._payload("TRAINER"))
        assert result["role"] == "TRAINER"

    def test_participant_blocked_with_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep(self._payload("PARTICIPANT"))
        assert exc_info.value.status_code == 403

    def test_missing_role_blocked_with_403(self):
        dep = require_role("TRAINER")
        with pytest.raises(HTTPException) as exc_info:
            dep({"sub": "1", "exp": int(time.time()) + 3600})
        assert exc_info.value.status_code == 403

    def test_case_insensitive(self):
        dep = require_role("trainer")
        result = dep(self._payload("TRAINER"))
        assert result["role"] == "TRAINER"


# ---------------------------------------------------------------------------
# HTTP-level tests: 401 on unauthenticated write requests
# MongoDB startup is patched out — auth runs before any DB access
# ---------------------------------------------------------------------------

class TestWriteEndpointsRequireAuth:
    def _make_client(self):
        """Context: TestClient with MongoDB init patched to a no-op."""
        from unittest.mock import AsyncMock, patch
        return patch("main.init_db", new_callable=AsyncMock)

    def test_create_question_no_token_returns_401(self):
        with self._make_client():
            with TestClient(app) as client:
                resp = client.post("/v1/api/questions/", json={
                    "question_type": "mcq",
                    "question_text": "What is 2+2?",
                    "options": [{"text": "3"}, {"text": "4"}],
                    "correct_answers": [1],
                    "skills": [],
                    "tags": [],
                })
        assert resp.status_code == 401

    def test_create_question_invalid_token_returns_401(self):
        with self._make_client():
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/api/questions/",
                    headers={"Authorization": "Bearer invalid.token.here"},
                    json={
                        "question_type": "mcq",
                        "question_text": "Test?",
                        "options": [{"text": "A"}, {"text": "B"}],
                        "correct_answers": [0],
                        "skills": [],
                        "tags": [],
                    },
                )
        assert resp.status_code == 401

    def test_create_question_participant_role_returns_403(self):
        token = _make_token(role="PARTICIPANT")
        with self._make_client():
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/api/questions/",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "question_type": "mcq",
                        "question_text": "Test?",
                        "options": [{"text": "A"}, {"text": "B"}],
                        "correct_answers": [0],
                        "skills": [],
                        "tags": [],
                    },
                )
        assert resp.status_code == 403

    def test_delete_question_no_token_returns_401(self):
        with self._make_client():
            with TestClient(app) as client:
                resp = client.delete("/v1/api/questions/some-id")
        assert resp.status_code == 401

    def test_update_question_no_token_returns_401(self):
        with self._make_client():
            with TestClient(app) as client:
                resp = client.put(
                    "/v1/api/questions/some-id",
                    json={"question_text": "Updated?"},
                )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self):
        token = _make_token(expired=True)
        with self._make_client():
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/api/questions/",
                    headers={"Authorization": f"Bearer {token}"},
                    json={},
                )
        assert resp.status_code == 401
