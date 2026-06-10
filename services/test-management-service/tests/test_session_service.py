"""Unit tests for SessionService.

No DB or network required — SessionRepository and the question-service httpx
client are patched with AsyncMocks. Service methods are async; driven with
asyncio.run() to match the repo's existing test style.
"""
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from src.models.session import SessionStatus
from src.schemas.session_schema import DraftSaveResult, SanitizedQuestion, SessionOut
from src.services.session_service import (
    EmptyQuestionBankError,
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
    SessionService,
    SessionTerminalError,
)

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


def _run(test=None, questions=None, existing=None, create_side_effect=None,
         current_question=None):
    """Drive create_session with the repositories + question client patched.

    ``existing`` feeds get_active_for_user_test (a list becomes a side_effect
    sequence for the IntegrityError-race test). Returns
    (SessionOut, captured_session_model) — the captured model is None when no
    new row was created (reuse path)."""
    captured = {}

    async def _capture_create(db, session):
        captured["session"] = session
        return session

    with patch(f"{SVC}.SessionRepository.get_test", new_callable=AsyncMock) as get_test, \
         patch(f"{SVC}.SessionRepository.get_active_for_user_test",
               new_callable=AsyncMock) as get_active, \
         patch(f"{SVC}.SessionRepository.flush", new_callable=AsyncMock), \
         patch(f"{SVC}.SessionRepository.create",
               side_effect=create_side_effect or _capture_create), \
         patch(f"{SVC}.question_client.sample_questions", new_callable=AsyncMock) as sample, \
         patch(f"{SVC}.question_client.get_question", new_callable=AsyncMock) as get_q:
        get_test.return_value = test
        if isinstance(existing, list):
            get_active.side_effect = existing
        else:
            get_active.return_value = existing
        sample.return_value = questions
        get_q.return_value = current_question or _question("q-current")
        out = asyncio.run(SessionService.create_session(AsyncMock(), 1, 42))
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


# ---- active-session reuse (W3-F7 item 3) ------------------------------------

def _active_row(current_index=1, expires_in=1800, draft_answers=None,
                question_ids=("a", "b", "c")):
    return SimpleNamespace(
        session_id=uuid4(),
        test_id=1,
        user_id=42,
        session_token="ab" * 32,
        server_now=datetime.utcnow() - timedelta(seconds=60),
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        status=SessionStatus.ACTIVE,
        current_index=current_index,
        question_ids=list(question_ids),
        draft_answers=draft_answers,
    )


def test_reuse_returns_existing_active_session_without_resampling():
    row = _active_row(current_index=1, draft_answers={"a": [1]})
    out, created = _run(_test_row(), [_question("fresh")], existing=row,
                        current_question=_question("b"))
    assert created is None                       # no duplicate row minted
    assert out.session_id == row.session_id
    assert out.session_token == row.session_token
    assert out.current_index == 1                # progress intact
    assert out.total_questions == 3
    assert out.question.id == "b"                # the question AT current_index
    assert out.draft_answers == {"a": [1]}       # autosave restored
    assert out.expires_at == row.expires_at      # original clock, not reset


def test_reuse_expired_active_is_flipped_and_fresh_session_minted():
    row = _active_row(expires_in=-10)
    out, created = _run(_test_row(), [_question("q1")], existing=row)
    assert row.status == SessionStatus.EXPIRED   # side-effect transition
    assert created is not None                   # fresh mint proceeded
    assert out.session_id == created.session_id
    assert out.session_id != row.session_id
    assert out.draft_answers is None


def test_lost_insert_race_serves_the_winner_row():
    """Losing the uq_sessions_active_user_test race must return the winner's
    session, not bubble a 500 (W3-F7 item 3, unlike cohort #73)."""
    from sqlalchemy.exc import IntegrityError

    winner = _active_row(current_index=0, question_ids=("a", "b", "c"))

    async def _duplicate_insert(db, session):
        raise IntegrityError(
            "INSERT INTO sessions", {}, Exception("uq_sessions_active_user_test")
        )

    out, _ = _run(_test_row(), [_question("q1")],
                  existing=[None, winner],       # lookup misses, then sees winner
                  create_side_effect=_duplicate_insert,
                  current_question=_question("a"))
    assert out.session_id == winner.session_id
    assert out.question.id == "a"


# ---- save_draft (W3-F4 autosave) -------------------------------------------

def _session_row(user_id=42, status=SessionStatus.ACTIVE, expires_in=1800,
                 current_index=2):
    return SimpleNamespace(
        session_id=uuid4(),
        user_id=user_id,
        status=status,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        current_index=current_index,
        draft_answers=None,
    )


def _run_draft(session, answers, user_id=42):
    """Drive save_draft with get_by_id/flush patched and an AsyncMock db."""
    db = AsyncMock()
    with patch(f"{SVC}.SessionRepository.get_by_id", new_callable=AsyncMock) as get_by_id, \
         patch(f"{SVC}.SessionRepository.flush", new_callable=AsyncMock):
        get_by_id.return_value = session
        return asyncio.run(
            SessionService.save_draft(db, session.session_id if session else uuid4(),
                                      user_id, answers)
        )


def test_save_draft_persists_without_advancing():
    session = _session_row(current_index=2)
    answers = {"q1": [1], "q2": [3, 4]}
    out = _run_draft(session, answers)
    assert isinstance(out, DraftSaveResult)
    assert session.draft_answers == answers       # persisted verbatim
    assert out.current_index == 2                 # unchanged
    assert out.status == "ACTIVE"                 # unchanged


def test_save_draft_missing_session_raises_not_found():
    with pytest.raises(SessionNotFoundError):
        _run_draft(None, {"q1": [1]})


def test_save_draft_wrong_user_raises_forbidden():
    session = _session_row(user_id=99)
    with pytest.raises(SessionForbiddenError):
        _run_draft(session, {"q1": [1]}, user_id=42)


def test_save_draft_terminal_session_raises_409():
    session = _session_row(status=SessionStatus.SUBMITTED)
    with pytest.raises(SessionTerminalError):
        _run_draft(session, {"q1": [1]})


def test_save_draft_expired_session_raises_and_marks_expired():
    session = _session_row(expires_in=-10)  # already past expires_at
    with pytest.raises(SessionExpiredError):
        _run_draft(session, {"q1": [1]})
    assert session.status == SessionStatus.EXPIRED
