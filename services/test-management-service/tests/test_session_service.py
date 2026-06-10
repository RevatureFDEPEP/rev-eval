"""Unit tests for SessionService.

No DB or network required — SessionRepository and the question-service httpx
client are patched with AsyncMocks. Service methods are async; driven with
asyncio.run() to match the repo's existing test style.
"""
import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from src.schemas.session_schema import SanitizedQuestion, SessionOut
from src.services.session_service import EmptyQuestionBankError, SessionService

SVC = "src.services.session_service"


def _test_row(test_id=1, duration_seconds=1800, number_of_questions=3):
    duration = timedelta(seconds=duration_seconds) if duration_seconds is not None else None
    return SimpleNamespace(
        id=test_id, duration=duration, number_of_questions=number_of_questions
    )


def _question(qid="q1", qtype="mcq"):
    """A full QMS question body, including answer fields that must be stripped."""
    return {
        "id": qid,
        "type": qtype,
        "question_text": "What is 2 + 2?",
        "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}],
        "difficulty": "easy",
        "image_url": None,
        "correct_answers": [2],
        "sample_answer": "secret",
    }


def _run(test=None, questions=None):
    """Drive create_session with get_test/create/sample_questions patched.

    Returns (SessionOut, captured_session_model)."""
    captured = {}

    async def _capture_create(db, session):
        captured["session"] = session
        return session

    with patch(f"{SVC}.SessionRepository.get_test", new_callable=AsyncMock) as get_test, \
         patch(f"{SVC}.SessionRepository.create", side_effect=_capture_create), \
         patch(f"{SVC}.question_client.sample_questions", new_callable=AsyncMock) as sample:
        get_test.return_value = test
        sample.return_value = questions
        out = asyncio.run(SessionService.create_session(None, 1, 42))
    return out, captured.get("session")


def test_returns_session_out_contract():
    out, _ = _run(_test_row(), [_question("q1"), _question("q2"), _question("q3")])
    assert isinstance(out, SessionOut)
    assert isinstance(out.session_id, UUID)
    assert out.current_index == 0
    assert out.total_questions == 3
    assert isinstance(out.question, SanitizedQuestion)


def test_timing_is_server_authoritative():
    out, _ = _run(_test_row(duration_seconds=1800), [_question()])
    # expires_at derived from server_now + test.duration, computed server-side.
    assert out.expires_at - out.server_now == timedelta(seconds=1800)


def test_duration_falls_back_when_null():
    out, _ = _run(_test_row(duration_seconds=None, number_of_questions=1), [_question()])
    assert out.expires_at - out.server_now == timedelta(seconds=3600)


def test_session_token_is_opaque_hex():
    out, _ = _run(_test_row(), [_question()])
    assert len(out.session_token) == 64  # secrets.token_hex(32)
    int(out.session_token, 16)  # valid hex, raises otherwise


def test_question_ids_persisted_and_index_zero():
    _, session = _run(_test_row(), [_question("a"), _question("b")])
    assert session.question_ids == ["a", "b"]
    assert session.current_index == 0


def test_first_question_strips_answer_fields():
    out, _ = _run(_test_row(), [_question("q1")])
    dumped = out.question.model_dump()
    assert "correct_answers" not in dumped
    assert "sample_answer" not in dumped
    assert dumped["id"] == "q1"


def test_accepts_mongo_id_alias_key():
    q = _question()
    del q["id"]
    q["_id"] = "abc123"
    out, session = _run(_test_row(number_of_questions=1), [q])
    assert out.question.id == "abc123"
    assert session.question_ids == ["abc123"]


def test_missing_test_raises_value_error():
    with pytest.raises(ValueError, match="Test not found"):
        _run(None, [_question()])


def test_empty_question_bank_raises():
    with pytest.raises(EmptyQuestionBankError):
        _run(_test_row(), [])
