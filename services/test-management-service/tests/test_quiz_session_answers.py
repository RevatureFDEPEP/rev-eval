"""Tests for the answer-submission state machine — Feature 2.

DB and repositories are mocked; the scoring module runs for real so these
also exercise the service-to-scoring integration.
"""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import all models so SQLAlchemy can configure mappers before the service
# instantiates QuizAnswer / IdempotencyKey ORM objects.
import src.models.idempotency_key  # noqa: F401
import src.models.quiz_answer  # noqa: F401
import src.models.quiz_session  # noqa: F401
import src.models.skill  # noqa: F401
import src.models.test  # noqa: F401
import src.models.test_skill  # noqa: F401
import src.models.test_submission  # noqa: F401
from fastapi import HTTPException
from src.models.idempotency_key import IdempotencyKey
from src.models.quiz_session import SessionStatus
from src.schemas.quiz_session_schema import AnswerSubmit
from src.services.quiz_answer_service import QuizAnswerService, _request_hash

SVC = "src.services.quiz_answer_service"


def _make_session(**overrides):
    session = MagicMock()
    session.id = 1
    session.session_id = "11111111-1111-1111-1111-111111111111"
    session.user_id = 7
    session.session_token = "tok"
    session.status = SessionStatus.in_progress
    session.current_index = 0
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    session.submitted_at = None
    for k, v in overrides.items():
        setattr(session, k, v)
    return session


def _make_snapshot(index, question_id, qtype="mcq", correct=None):
    snap = MagicMock()
    snap.question_id = question_id
    snap.question_index = index
    snap.question_type = qtype
    snap.snapshot_json = {
        "_id": question_id,
        "type": qtype,
        "question_text": f"Question {index} text here?",
        "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
        "correct_answers": correct if correct is not None else [2],
    }
    return snap


def _payload(question_id="q0", answers=None, token="tok"):
    return AnswerSubmit(
        session_token=token,
        question_id=question_id,
        answers=answers if answers is not None else [2],
    )


def _patches(session, questions, idem_get=None, existing_answer=None):
    return [
        patch(f"{SVC}.QuizSessionRepository.get_for_update", new=AsyncMock(return_value=session)),
        patch(f"{SVC}.QuizSessionRepository.get_questions_for_session", new=AsyncMock(return_value=questions)),
        patch(f"{SVC}.IdempotencyRepository.get", new=AsyncMock(return_value=idem_get)),
        patch(f"{SVC}.IdempotencyRepository.add", new=AsyncMock()),
        patch(f"{SVC}.QuizAnswerRepository.add", new=AsyncMock()),
        patch(f"{SVC}.QuizAnswerRepository.get_by_session_and_index", new=AsyncMock(return_value=existing_answer)),
    ]


async def _run(session, questions, payload, key="key-1", user=None, idem_get=None, existing_answer=None):
    user = user or {"id": 7, "role": "PARTICIPANT"}
    mock_db = AsyncMock()
    session_id = session.session_id if session is not None else "00000000-0000-0000-0000-000000000000"
    with ExitStack() as stack:
        for p in _patches(session, questions, idem_get=idem_get, existing_answer=existing_answer):
            stack.enter_context(p)
        return await QuizAnswerService.submit_answer(
            mock_db, session_id, payload, key, user
        )


# ---------------------------------------------------------------------------
# Happy path + advance/finish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_advances_to_next_question():
    session = _make_session()
    questions = [_make_snapshot(0, "q0"), _make_snapshot(1, "q1")]

    ack = await _run(session, questions, _payload("q0", [2]))

    assert ack.recorded is True
    assert ack.current_index == 1
    assert ack.finished is False
    assert ack.status == "in_progress"
    assert ack.next_question is not None
    assert ack.next_question.question_id == "q1"
    # never leaks correctness
    assert not hasattr(ack, "is_correct")
    assert not hasattr(ack, "earned")


@pytest.mark.asyncio
async def test_submit_last_question_finalizes_session():
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    ack = await _run(session, questions, _payload("q0", [2]))

    assert ack.finished is True
    assert ack.status == "submitted"
    assert ack.next_question is None
    assert session.status == SessionStatus.submitted
    assert session.submitted_at is not None


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_replay_returns_prior_response_without_mutation():
    session = _make_session()
    questions = [_make_snapshot(0, "q0"), _make_snapshot(1, "q1")]
    payload = _payload("q0", [2])

    prior = MagicMock()
    prior.request_hash = _request_hash(payload)
    prior.response_json = {
        "question_id": "q0",
        "recorded": True,
        "current_index": 1,
        "status": "in_progress",
        "finished": False,
        "next_question": None,
    }

    ack = await _run(session, questions, payload, idem_get=prior)

    assert ack.current_index == 1
    # session cursor untouched by a replay
    assert session.current_index == 0


@pytest.mark.asyncio
async def test_idempotency_key_reuse_with_different_body_conflicts():
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    prior = MagicMock()
    prior.request_hash = "a-different-hash"
    prior.response_json = {}

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2]), idem_get=prior)

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# State-machine rejections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submitted_session_rejects_further_answers():
    session = _make_session(status=SessionStatus.submitted)
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2]))

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_expired_session_is_rejected_and_marked_expired():
    session = _make_session(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2]))

    assert exc.value.status_code == 409
    assert session.status == SessionStatus.expired


@pytest.mark.asyncio
async def test_missing_session_returns_404():
    with pytest.raises(HTTPException) as exc:
        await _run(None, [], _payload("q0", [2]))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_foreign_user_rejected_403():
    session = _make_session(user_id=999)
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2]))

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_bad_session_token_rejected_403():
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2], token="wrong"))

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_non_ascii_session_token_rejected_403():
    """Client-controlled non-ASCII tokens must reject, not crash compare_digest."""
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2], token="wrong-non-ascii-\u00f1"))

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_out_of_order_answer_conflicts():
    session = _make_session(current_index=1)
    questions = [_make_snapshot(0, "q0"), _make_snapshot(1, "q1")]

    # submitting q0 while the cursor is at index 1
    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("q0", [2]))

    assert exc.value.status_code == 409


def test_idempotency_key_created_at_default_is_timezone_aware():
    created_at = IdempotencyKey.__table__.c.created_at.default.arg(None)

    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timedelta(0)


@pytest.mark.asyncio
async def test_unknown_question_returns_422():
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(session, questions, _payload("does-not-exist", [2]))

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_already_answered_index_conflicts_409():
    """S5: a pre-existing answer row at the current index is rejected cleanly."""
    session = _make_session()
    questions = [_make_snapshot(0, "q0")]

    with pytest.raises(HTTPException) as exc:
        await _run(
            session, questions, _payload("q0", [2]), existing_answer=MagicMock()
        )

    assert exc.value.status_code == 409
