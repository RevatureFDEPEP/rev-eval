"""Unit tests for the quiz-session Pydantic schemas (W3-F1, Part B).

Pure validation — no DB, no async, no app/route/model import — so the suite
needs only pytest + the service requirements and the route/model code stays out
of the coverage denominator. Locks the canonical contract field names the
frontend mirrors and the answer-key-omission of ``QuizQuestionOut``.
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from src.schemas.quiz_session_schema import (
    QuizQuestionOut,
    SessionCreate,
    SessionRead,
)

# ---------------------------------------------------------------------------
# SessionCreate
# ---------------------------------------------------------------------------


def test_session_create_minimal():
    s = SessionCreate(test_id=7)
    assert s.test_id == 7
    assert s.submission_id is None


def test_session_create_with_submission():
    s = SessionCreate(test_id=7, submission_id=42)
    assert s.submission_id == 42


def test_session_create_requires_test_id():
    with pytest.raises(ValidationError):
        SessionCreate(submission_id=1)


def test_session_create_test_id_coerces_numeric_string():
    s = SessionCreate(test_id="7")
    assert s.test_id == 7


# ---------------------------------------------------------------------------
# QuizQuestionOut  (answer-key safety)
# ---------------------------------------------------------------------------


def test_quiz_question_out_fields():
    q = QuizQuestionOut(
        question_id="abc",
        question_text="What is 2+2?",
        question_type="mcq",
        difficulty="easy",
        options=[{"option_id": 1, "text": "4"}],
    )
    assert q.question_id == "abc"
    assert q.options == [{"option_id": 1, "text": "4"}]


def test_quiz_question_out_options_optional():
    q = QuizQuestionOut(
        question_id="tf",
        question_text="The sky is blue.",
        question_type="true_false",
        difficulty="easy",
    )
    assert q.options is None


def test_quiz_question_out_has_no_answer_fields():
    fields = set(QuizQuestionOut.model_fields)
    assert "correct_answers" not in fields
    assert "sample_answer" not in fields
    assert "answer_explanation" not in fields
    assert fields == {
        "question_id",
        "question_text",
        "question_type",
        "difficulty",
        "options",
    }


# ---------------------------------------------------------------------------
# SessionRead
# ---------------------------------------------------------------------------


def test_session_read_full_shape():
    now = datetime(2026, 6, 17, 12, 0, 0)
    q = QuizQuestionOut(
        question_id="q1",
        question_text="q?",
        question_type="mcq",
        difficulty="medium",
        options=[{"option_id": 1, "text": "a"}, {"option_id": 2, "text": "b"}],
    )
    sr = SessionRead(
        session_id="sess-123",
        session_token="tok",
        test_id=5,
        user_id=9,
        status="in_progress",
        current_index=0,
        server_now=now,
        expires_at=now + timedelta(hours=1),
        first_question=q,
        questions=[q],
    )
    assert sr.session_id == "sess-123"
    assert sr.first_question.question_id == "q1"
    assert sr.questions[0].question_id == "q1"
    assert set(SessionRead.model_fields) == {
        "session_id",
        "session_token",
        "test_id",
        "user_id",
        "status",
        "current_index",
        "server_now",
        "expires_at",
        "first_question",
        "questions",
    }


def test_session_read_first_question_nullable():
    now = datetime(2026, 6, 17, 12, 0, 0)
    sr = SessionRead(
        session_id="s",
        session_token="t",
        test_id=1,
        user_id=1,
        status="in_progress",
        current_index=0,
        server_now=now,
        expires_at=now,
        first_question=None,
    )
    assert sr.first_question is None
    assert sr.questions == []
