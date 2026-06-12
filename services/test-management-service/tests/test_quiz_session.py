"""
Tests for quiz session creation — Feature 1.

Pure-function tests run without a DB or network.
Service-level tests mock the DB session and httpx client.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import src.models.quiz_session  # noqa: F401

# Env vars and sys.path are configured in conftest.py, which pytest loads
# before this module is imported.
# All models must be imported so SQLAlchemy can configure its mappers before
# any ORM class is instantiated below (Test declares a relationship to
# TestSubmission by name).
import src.models.skill  # noqa: F401
import src.models.test  # noqa: F401
import src.models.test_skill  # noqa: F401
import src.models.test_submission  # noqa: F401
from src.schemas.quiz_session_schema import QuizSessionCreate
from src.services.quiz_session_service import (
    _SENSITIVE_QUESTION_FIELDS,
    QuizSessionService,
    _strip_correct_answers,
    compute_expires_at,
)

# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


class TestComputeExpiresAt:
    def test_duration_adds_to_server_now(self):
        now = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
        duration = timedelta(minutes=90)
        result = compute_expires_at(now, duration)
        assert result == datetime(2026, 6, 11, 13, 30, 0, tzinfo=timezone.utc)

    def test_zero_duration(self):
        now = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(now, timedelta(0))
        assert result == now

    def test_none_duration_falls_back_to_one_hour(self):
        now = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(now, None)
        assert result == datetime(2026, 6, 11, 13, 0, 0, tzinfo=timezone.utc)


class TestStripCorrectAnswers:
    def test_removes_correct_answers_field(self):
        q = {
            "_id": "abc123",
            "type": "mcq",
            "question_text": "What is 2+2?",
            "options": [{"text": "3"}, {"text": "4"}],
            "correct_answers": [2],
            "answer_explanation": "Basic arithmetic.",
            "sample_answer": None,
        }
        out = _strip_correct_answers(q)
        assert not hasattr(out, "correct_answers")
        assert not hasattr(out, "answer_explanation")
        assert not hasattr(out, "sample_answer")

    def test_preserves_safe_fields(self):
        q = {
            "_id": "abc123",
            "type": "multi",
            "question_text": "Select all valid HTTP methods.",
            "options": [{"text": "GET"}, {"text": "POST"}, {"text": "DRINK"}],
            "correct_answers": [1, 2],
        }
        out = _strip_correct_answers(q)
        assert out.question_id == "abc123"
        assert out.question_type == "multi"
        assert out.question_text == "Select all valid HTTP methods."
        assert len(out.options) == 3

    def test_falls_back_to_id_key_when_no_underscore_id(self):
        q = {
            "id": "mongo-id-999",
            "type": "true_false",
            "question_text": "Python is a compiled language.",
            "options": None,
            "correct_answers": [False],
        }
        out = _strip_correct_answers(q)
        assert out.question_id == "mongo-id-999"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestQuizSessionCreateSchema:
    def test_requires_test_id(self):
        s = QuizSessionCreate(test_id=5)
        assert s.test_id == 5
        assert s.submission_id is None

    def test_accepts_optional_submission_id(self):
        s = QuizSessionCreate(test_id=3, submission_id=42)
        assert s.submission_id == 42


# ---------------------------------------------------------------------------
# Service-level tests (mocked DB + httpx)
# ---------------------------------------------------------------------------


def _make_mock_test(test_id=1, number_of_questions=2, duration=timedelta(minutes=30), active=True):
    test = MagicMock()
    test.id = test_id
    test.number_of_questions = number_of_questions
    test.duration = duration
    test.active = active
    return test


def _make_mock_question(idx: int):
    return {
        "_id": f"q{idx}",
        "type": "mcq",
        "question_text": f"Question {idx} text here?",
        "options": [{"text": "A"}, {"text": "B"}],
        "correct_answers": [1],
    }


def _patch_create_session(mock_test, questions=None, active_count=0):
    """Patch the repo/HTTP collaborators of create_session.

    Returns a list of context managers to enter. _fetch_questions is patched
    when `questions` is provided; otherwise the caller patches httpx itself.
    """
    patches = [
        patch(
            "src.services.quiz_session_service.TestRepository.get_by_id",
            new=AsyncMock(return_value=mock_test),
        ),
        patch(
            "src.services.quiz_session_service.QuizSessionRepository.count_active_for_user",
            new=AsyncMock(return_value=active_count),
        ),
    ]
    if questions is not None:
        patches.append(
            patch(
                "src.services.quiz_session_service._fetch_questions",
                new=AsyncMock(return_value=questions),
            )
        )
    return patches


@pytest.mark.asyncio
async def test_create_session_returns_start_response():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # AsyncSession.add is synchronous
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    questions = [_make_mock_question(i) for i in range(2)]
    mock_test = _make_mock_test()

    p1, p2, p3 = _patch_create_session(mock_test, questions=questions)
    with p1, p2, p3:
        result = await QuizSessionService.create_session(
            db=mock_db,
            payload=QuizSessionCreate(test_id=1),
            current_user={"id": 7, "role": "PARTICIPANT", "email": "p@test.com"},
        )

    assert result.session_id is not None
    assert result.session_token != ""
    assert result.status == "in_progress"
    assert result.current_index == 0
    assert result.question.question_id == "q0"
    assert not hasattr(result.question, "correct_answers")
    assert result.expires_at > result.server_now


@pytest.mark.asyncio
async def test_create_session_response_question_has_no_sensitive_fields():
    """H3 regression: the served question must not carry any answer fields."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # AsyncSession.add is synchronous
    questions = [_make_mock_question(0)]
    mock_test = _make_mock_test(number_of_questions=1)

    p1, p2, p3 = _patch_create_session(mock_test, questions=questions)
    with p1, p2, p3:
        result = await QuizSessionService.create_session(
            db=mock_db,
            payload=QuizSessionCreate(test_id=1),
            current_user={"id": 7, "role": "PARTICIPANT"},
        )

    served = result.question.model_dump()
    for field in _SENSITIVE_QUESTION_FIELDS:
        assert field not in served


@pytest.mark.asyncio
async def test_create_session_missing_test_raises_404():
    from fastapi import HTTPException

    mock_db = AsyncMock()

    with patch(
        "src.services.quiz_session_service.TestRepository.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=999),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_session_inactive_test_raises_403():
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_test = _make_mock_test(active=False)

    with patch(
        "src.services.quiz_session_service.TestRepository.get_by_id",
        new=AsyncMock(return_value=mock_test),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=1),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_session_foreign_submission_raises_403():
    """H2 regression: a submission owned by another user must be rejected."""
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_test = _make_mock_test()

    foreign_submission = MagicMock()
    foreign_submission.user_id = 999  # not the requesting user
    foreign_submission.test_id = 1

    with (
        patch(
            "src.services.quiz_session_service.TestRepository.get_by_id",
            new=AsyncMock(return_value=mock_test),
        ),
        patch(
            "src.services.quiz_session_service.TestSubmissionRepository.get_by_id",
            new=AsyncMock(return_value=foreign_submission),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=1, submission_id=42),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_session_too_many_active_raises_429():
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_test = _make_mock_test()

    p1, p2 = _patch_create_session(mock_test, active_count=1000)
    with p1, p2:
        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=1),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_create_session_empty_question_pool_raises_503():
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_test = _make_mock_test()

    empty_response = MagicMock()
    empty_response.status_code = 200
    empty_response.json.return_value = []

    p1, p2 = _patch_create_session(mock_test)
    with p1, p2, patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=empty_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=1),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_create_session_question_service_unreachable_raises_503():
    import httpx as _httpx
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_test = _make_mock_test()

    p1, p2 = _patch_create_session(mock_test)
    with p1, p2, patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=_httpx.RequestError("timeout"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await QuizSessionService.create_session(
                db=mock_db,
                payload=QuizSessionCreate(test_id=1),
                current_user={"id": 7, "role": "PARTICIPANT"},
            )

    assert exc_info.value.status_code == 503
