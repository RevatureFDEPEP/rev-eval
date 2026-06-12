"""Schema-level tests for the quiz-session request/response models."""
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.schemas.session_schema import (
    SanitizedQuestion,
    SessionCreate,
    SessionResponse,
)


def test_session_create_requires_test_id():
    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_accepts_test_id():
    assert SessionCreate(test_id=7).test_id == 7


def test_sanitized_question_drops_answer_fields():
    # Extra fields (incl. the answer key) are ignored, not stored.
    q = SanitizedQuestion(
        id="q1",
        type="mcq",
        question_text="What is 2+2?",
        options=[{"option_text": "4"}],
        difficulty="easy",
        correct_answers=[1],
        sample_answer="4",
    )
    assert q.id == "q1"
    assert not hasattr(q, "correct_answers")
    assert "correct_answers" not in q.model_dump()


def test_session_response_round_trip():
    now = datetime(2026, 6, 11, 12, 0, 0)
    resp = SessionResponse(
        session_id="abc-123",
        session_token="deadbeef",
        server_now=now,
        expires_at=now + timedelta(minutes=60),
        current_index=0,
        total_questions=5,
        question={"id": "q1", "type": "mcq", "question_text": "What is 2+2?"},
    )
    assert resp.session_id == "abc-123"
    assert resp.question.id == "q1"
    assert resp.total_questions == 5
    assert resp.current_index == 0
    assert resp.draft_answers is None
    assert (resp.expires_at - resp.server_now) == timedelta(minutes=60)


def test_session_response_question_optional():
    now = datetime(2026, 6, 11, 12, 0, 0)
    resp = SessionResponse(
        session_id="abc-123",
        session_token="deadbeef",
        server_now=now,
        expires_at=now,
        current_index=0,
        total_questions=0,
    )
    assert resp.question is None
