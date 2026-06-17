"""Tests for POST /sessions/{id}/answer — lock / idempotency / state machine.

Service-level tests drive ``SessionService.submit_answer`` directly with the
repositories and the question-service client patched (no DB, no network), in
the ``asyncio.run`` + ``AsyncMock`` style of the existing suite. One route-level
test exercises the required-header (422) contract through a FastAPI TestClient.

The real-Postgres ``SELECT FOR UPDATE`` race is out of scope here — it is
covered against a live database in W3-F5.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.models.answer import GradingStatus
from src.models.session import SessionStatus
from src.services.session_service import (
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
    SessionService,
    SessionTerminalError,
)

SVC = "src.services.session_service"
SID = uuid4()
USER_ID = 42


def _session(status=SessionStatus.ACTIVE, current_index=0, question_ids=None,
             user_id=USER_ID, expires_at=None):
    from datetime import datetime, timedelta
    return SimpleNamespace(
        session_id=SID,
        user_id=user_id,
        status=status,
        current_index=current_index,
        question_ids=question_ids if question_ids is not None else ["q0", "q1", "q2"],
        submitted_at=None,
        expires_at=expires_at or (datetime.utcnow() + timedelta(hours=1)),
    )


def _question(qid="q0", qtype="mcq", correct=None):
    return {
        "id": qid,
        "type": qtype,
        "question_text": "What is 2 + 2?",
        "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}],
        "difficulty": "easy",
        "image_url": None,
        "correct_answers": correct if correct is not None else [2],
        "sample_answer": "secret",
    }


def _run(session, submitted, *, idem_existing=None, questions=None, key="key-1",
         user_id=USER_ID, pending_count=0):
    """Drive submit_answer with all repos + question_client patched.

    ``questions`` maps qid -> question dict for get_question lookups.
    Returns (result_or_exc, captured) where captured holds the Answer row and
    any stored idempotency record."""
    captured = {}
    qids = (session.question_ids or []) if session is not None else []
    qmap = questions or {qid: _question(qid) for qid in qids}

    async def _get_question(qid):
        return qmap[qid]

    async def _capture_answer(db, answer):
        captured["answer"] = answer
        return answer

    async def _capture_idem(db, record):
        captured["idem"] = record
        return record

    db = AsyncMock()  # db.commit() awaitable

    with patch(f"{SVC}.SessionRepository.get_for_update", new_callable=AsyncMock) as gfu, \
         patch(f"{SVC}.SessionRepository.flush", new_callable=AsyncMock), \
         patch(f"{SVC}.IdempotencyRepository.get", new_callable=AsyncMock) as iget, \
         patch(f"{SVC}.IdempotencyRepository.create", side_effect=_capture_idem), \
         patch(f"{SVC}.AnswerRepository.create", side_effect=_capture_answer), \
         patch(f"{SVC}.AnswerRepository.count_pending", new_callable=AsyncMock) as cpend, \
         patch(f"{SVC}.question_client.get_question", side_effect=_get_question) as gq:
        gfu.return_value = session
        iget.return_value = idem_existing
        cpend.return_value = pending_count
        captured["count_pending"] = cpend
        captured["get_question"] = gq
        try:
            out = asyncio.run(
                SessionService.submit_answer(db, SID, user_id, submitted, key)
            )
        except Exception as e:  # noqa: BLE001 — return for assertion
            return e, captured
    captured["db"] = db
    return out, captured


def test_happy_path_scores_and_advances():
    out, cap = _run(_session(current_index=0), [2])
    assert out.current_index == 1                 # advanced
    assert out.status == "ACTIVE"
    assert out.next_question is not None
    assert out.question_id == "q0"
    # scored Answer persisted with correct score
    assert cap["answer"].is_correct is True
    assert cap["answer"].score == 1.0
    assert cap["answer"].question_index == 0
    cap["db"].commit.assert_awaited()


def test_score_hidden_from_response():
    out, _ = _run(_session(), [2])
    body = out.model_dump()
    assert "score" not in body
    assert "is_correct" not in body


def test_wrong_answer_still_advances():
    out, cap = _run(_session(current_index=0), [1])
    assert cap["answer"].score == 0.0
    assert cap["answer"].is_correct is False
    assert out.current_index == 1                 # advances regardless of score


def test_final_question_finalizes_session():
    session = _session(current_index=2, question_ids=["q0", "q1", "q2"])
    out, cap = _run(session, [2])
    assert out.status == "SUBMITTED"
    assert out.submitted_at is not None
    assert out.next_question is None              # no next question
    assert session.status == SessionStatus.SUBMITTED


def test_text_answer_recorded_pending_review():
    # A free-text answer is staged PENDING_REVIEW, not a silent 0.0 (W5-F1).
    session = _session(current_index=0, question_ids=["q0"])
    questions = {"q0": _question("q0", qtype="text", correct=[])}
    out, cap = _run(session, ["my prose answer"], questions=questions, pending_count=1)
    assert out.status == "SUBMITTED"
    assert cap["answer"].grading_status == GradingStatus.PENDING_REVIEW
    assert cap["answer"].score == 0.0
    # The finalized session is flagged as needing a manual grade.
    assert session.needs_grading is True


def test_auto_only_session_does_not_need_grading():
    # Regression: an all-auto session finalizes without needs_grading (W5-F1).
    session = _session(current_index=2, question_ids=["q0", "q1", "q2"])
    out, cap = _run(session, [2], pending_count=0)
    assert out.status == "SUBMITTED"
    assert cap["answer"].grading_status == GradingStatus.AUTO
    assert session.needs_grading is False


def test_idempotency_replays_without_rescoring():
    stored = {
        "session_id": str(SID),
        "question_id": "q0",
        "current_index": 1,
        "total_questions": 3,
        "status": "ACTIVE",
        "submitted_at": None,
        "next_question": None,
    }
    out, cap = _run(_session(), [2], idem_existing=SimpleNamespace(response_body=stored))
    assert out.current_index == 1
    assert out.question_id == "q0"
    # scoring never invoked on replay, nothing committed
    cap["get_question"].assert_not_called()
    assert "answer" not in cap


def test_submitted_session_rejected_409():
    out, _ = _run(_session(status=SessionStatus.SUBMITTED), [2])
    assert isinstance(out, SessionTerminalError)


def test_expired_status_rejected_409():
    out, _ = _run(_session(status=SessionStatus.EXPIRED), [2])
    assert isinstance(out, SessionTerminalError)


def test_elapsed_expiry_transitions_and_rejects():
    from datetime import datetime, timedelta
    session = _session(expires_at=datetime.utcnow() - timedelta(seconds=1))
    out, _ = _run(session, [2])
    assert isinstance(out, SessionExpiredError)
    assert session.status == SessionStatus.EXPIRED   # transitioned as a side effect


def test_unknown_session_404():
    out, _ = _run(None, [2])
    assert isinstance(out, SessionNotFoundError)


def test_other_users_session_forbidden():
    out, _ = _run(_session(user_id=999), [2], user_id=USER_ID)
    assert isinstance(out, SessionForbiddenError)


def test_multi_select_partial_credit_recorded():
    session = _session(question_ids=["q0"])
    q = {"q0": _question("q0", qtype="multi", correct=[1, 2, 3, 4])}
    out, cap = _run(session, [1, 2], questions=q)
    assert cap["answer"].score == pytest.approx(0.5)
    assert cap["answer"].is_correct is False
    assert out.status == "SUBMITTED"             # single-question session finalizes


# --- route-level: required Idempotency-Key header ---

def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.db.session import get_db
    from src.utils.dependencies import get_current_user_from_headers
    from src.v1.routes.session_route import router

    app = FastAPI()
    app.include_router(router, prefix="/v1/api")
    app.dependency_overrides[get_current_user_from_headers] = lambda: {"id": USER_ID}
    app.dependency_overrides[get_db] = lambda: None
    return TestClient(app)


def test_missing_idempotency_key_returns_422():
    resp = _client().post(
        f"/v1/api/sessions/{SID}/answer", json={"submitted_answers": [2]}
    )
    assert resp.status_code == 422


def test_blank_idempotency_key_returns_422():
    resp = _client().post(
        f"/v1/api/sessions/{SID}/answer",
        json={"submitted_answers": [2]},
        headers={"Idempotency-Key": "   "},
    )
    assert resp.status_code == 422
