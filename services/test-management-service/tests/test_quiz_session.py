"""Integration tests for quiz session creation and safe question exposure."""
from datetime import datetime

import pytest
from conftest import make_test, sample_question_pool
from src.schemas.quiz_session_schema import QuizSessionCreate
from src.services import quiz_session_service
from src.services.quiz_session_service import QuizSessionService

PARTICIPANT = {"id": 1, "role": "PARTICIPANT"}


@pytest.fixture(autouse=True)
def _patch_question_fetch(monkeypatch):
    """Replace the live question-service call with a deterministic pool."""

    async def fake_fetch(n, correlation_id=None):
        return sample_question_pool()

    monkeypatch.setattr(quiz_session_service, "_fetch_questions", fake_fetch)


@pytest.mark.asyncio
async def test_create_session_is_server_timed_and_durable(async_session):
    test = await make_test(async_session, minutes=30)

    before = datetime.utcnow()
    resp = await QuizSessionService.create_session(
        async_session, QuizSessionCreate(test_id=test.id), PARTICIPANT
    )

    # Server-authoritative timing.
    assert resp.server_now >= before
    assert resp.expires_at > resp.server_now
    assert (resp.expires_at - resp.server_now).total_seconds() == pytest.approx(
        30 * 60, abs=5
    )

    # Durable handles.
    assert resp.session_id
    assert resp.session_token
    assert resp.status == "in_progress"
    assert resp.total_questions == 3
    assert resp.current_index == 0


@pytest.mark.asyncio
async def test_create_session_first_question_has_no_answer_keys(async_session):
    test = await make_test(async_session)
    resp = await QuizSessionService.create_session(
        async_session, QuizSessionCreate(test_id=test.id), PARTICIPANT
    )
    payload = resp.question.model_dump()
    assert "correct_answers" not in payload
    assert "answer_explanation" not in payload
    assert "sample_answer" not in payload
    assert payload["question_text"]


@pytest.mark.asyncio
async def test_get_session_returns_safe_questions_but_snapshot_keeps_keys(async_session):
    test = await make_test(async_session)
    created = await QuizSessionService.create_session(
        async_session, QuizSessionCreate(test_id=test.id), PARTICIPANT
    )

    state = await QuizSessionService.get_session(
        async_session, created.session_id, PARTICIPANT
    )
    assert len(state.questions) == 3
    for q in state.questions:
        dumped = q.model_dump()
        assert "correct_answers" not in dumped
        assert "answer_explanation" not in dumped

    # The server-only snapshot DOES retain the answer key for scoring.
    from src.repositories.quiz_session_repository import QuizSessionRepository

    session_row = await QuizSessionRepository.get_by_session_id(
        async_session, created.session_id
    )
    snapshots = await QuizSessionRepository.get_questions_for_session(
        async_session, session_row.id
    )
    assert any((s.snapshot_json or {}).get("correct_answers") for s in snapshots)


@pytest.mark.asyncio
async def test_create_session_rejects_inactive_test(async_session):
    from fastapi import HTTPException

    test = await make_test(async_session, active=False)
    with pytest.raises(HTTPException) as exc:
        await QuizSessionService.create_session(
            async_session, QuizSessionCreate(test_id=test.id), PARTICIPANT
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_session_rejects_non_owner(async_session):
    from fastapi import HTTPException

    test = await make_test(async_session)
    created = await QuizSessionService.create_session(
        async_session, QuizSessionCreate(test_id=test.id), PARTICIPANT
    )
    other = {"id": 999, "role": "PARTICIPANT"}
    with pytest.raises(HTTPException) as exc:
        await QuizSessionService.get_session(
            async_session, created.session_id, other
        )
    assert exc.value.status_code == 404
