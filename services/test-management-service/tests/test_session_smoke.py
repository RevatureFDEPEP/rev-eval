"""
Smoke tests for session schemas — no database required.

Covers: SessionCreate validation, SessionOut ORM coercion,
and SessionStartResponse field presence.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError
from src.models.session import SessionStatus
from src.schemas.session_schema import (
    SessionCreate,
    SessionOut,
    SessionStartResponse,
)

# ── SessionCreate ─────────────────────────────────────────────────────────────


def test_session_create_accepts_valid_test_id():
    sc = SessionCreate(test_id=42)
    assert sc.test_id == 42


def test_session_create_requires_test_id():
    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_rejects_non_integer_test_id():
    with pytest.raises(ValidationError):
        SessionCreate(test_id="not-an-int")


# ── SessionOut ────────────────────────────────────────────────────────────────


def test_session_out_reads_from_orm_attributes():
    now = datetime(2026, 6, 18, 10, 0, 0)
    exp = datetime(2026, 6, 18, 12, 0, 0)

    class FakeRow:
        session_id = "aaaa-bbbb-cccc"
        test_id = 5
        user_id = 99
        session_token = "deadbeef" * 8
        server_now = now
        expires_at = exp
        status = SessionStatus.ACTIVE
        current_index = 0

    out = SessionOut.model_validate(FakeRow())
    assert out.session_id == "aaaa-bbbb-cccc"
    assert out.test_id == 5
    assert out.user_id == 99
    assert out.status == SessionStatus.ACTIVE
    assert out.current_index == 0
    assert out.expires_at == exp


# ── SessionStartResponse ──────────────────────────────────────────────────────


def test_session_start_response_contains_all_required_fields():
    now = datetime(2026, 6, 18, 10, 0, 0)
    exp = datetime(2026, 6, 18, 12, 0, 0)
    resp = SessionStartResponse(
        session_id="test-uuid",
        session_token="tok" * 20,
        server_now=now,
        expires_at=exp,
    )
    assert resp.session_id == "test-uuid"
    assert resp.first_question is None  # optional, defaults to None


def test_session_start_response_accepts_first_question():
    now = datetime(2026, 6, 18, 10, 0, 0)
    exp = datetime(2026, 6, 18, 12, 0, 0)
    question = {"_id": "abc123", "question_text": "What is 2+2?", "type": "mcq"}
    resp = SessionStartResponse(
        session_id="test-uuid",
        session_token="tok" * 20,
        server_now=now,
        expires_at=exp,
        first_question=question,
    )
    assert resp.first_question["_id"] == "abc123"


# ── SessionStatus enum ────────────────────────────────────────────────────────


def test_session_status_values():
    assert SessionStatus.ACTIVE == "ACTIVE"
    assert SessionStatus.EXPIRED == "EXPIRED"
    assert SessionStatus.COMPLETED == "COMPLETED"
    assert SessionStatus.ABANDONED == "ABANDONED"
