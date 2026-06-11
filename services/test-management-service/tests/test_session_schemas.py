"""Schema-level tests for the quiz-session request/response models."""
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.schemas.session_schema import SessionCreate, SessionResponse


def test_session_create_requires_test_id():
    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_accepts_test_id():
    assert SessionCreate(test_id=7).test_id == 7


def test_session_response_round_trip():
    now = datetime(2026, 6, 11, 12, 0, 0)
    resp = SessionResponse(
        session_id="abc-123",
        session_token="deadbeef",
        server_now=now,
        expires_at=now + timedelta(minutes=60),
        first_question={"id": "q1", "type": "mcq", "question_text": "What is 2+2?"},
    )
    assert resp.session_id == "abc-123"
    assert resp.first_question["id"] == "q1"
    assert (resp.expires_at - resp.server_now) == timedelta(minutes=60)


def test_session_response_first_question_optional():
    now = datetime(2026, 6, 11, 12, 0, 0)
    resp = SessionResponse(
        session_id="abc-123",
        session_token="deadbeef",
        server_now=now,
        expires_at=now,
    )
    assert resp.first_question is None
