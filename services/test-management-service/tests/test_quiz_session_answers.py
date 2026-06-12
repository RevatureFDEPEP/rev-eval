"""Integration tests for answer scoring, idempotency, locking and immutability."""
import pytest
from conftest import make_test, sample_question_pool
from fastapi import HTTPException
from src.models.quiz_session import SessionStatus
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.schemas.quiz_session_schema import (
    AnswerSubmit,
    DraftPatch,
    QuizSessionCreate,
)
from src.services import quiz_session_service
from src.services.quiz_session_service import QuizSessionService

PARTICIPANT = {"id": 1, "role": "PARTICIPANT"}


@pytest.fixture(autouse=True)
def _patch_question_fetch(monkeypatch):
    async def fake_fetch(n, correlation_id=None):
        return sample_question_pool()

    monkeypatch.setattr(quiz_session_service, "_fetch_questions", fake_fetch)


async def _new_session(db):
    test = await make_test(db)
    created = await QuizSessionService.create_session(
        db, QuizSessionCreate(test_id=test.id), PARTICIPANT
    )
    return created.session_id


async def _expire(db, session_id):
    """Force a session past its deadline."""
    from datetime import datetime, timedelta

    row = await QuizSessionRepository.get_by_session_id(db, session_id)
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await db.commit()


@pytest.mark.asyncio
async def test_answer_is_scored_without_leaking_correctness(async_session):
    sid = await _new_session(async_session)
    resp = await QuizSessionService.submit_answer(
        async_session, sid, AnswerSubmit(question_id="q-mcq", selected_answers=[2]),
        PARTICIPANT,
    )
    dumped = resp.model_dump()
    assert dumped["recorded"] is True
    assert "is_correct" not in dumped
    assert "earned" not in dumped
    assert "score" not in dumped

    # But the server recorded the correct score internally.
    row = await QuizSessionRepository.get_by_session_id(async_session, sid)
    answers = await QuizSessionRepository.get_answers_for_session(async_session, row.id)
    assert len(answers) == 1
    assert answers[0].is_correct is True
    assert answers[0].earned == 1.0


@pytest.mark.asyncio
async def test_multi_select_partial_credit_recorded(async_session):
    sid = await _new_session(async_session)
    await QuizSessionService.submit_answer(
        async_session, sid,
        AnswerSubmit(question_id="q-multi", selected_answers=[1]),  # 1 of 2 right
        PARTICIPANT,
    )
    row = await QuizSessionRepository.get_by_session_id(async_session, sid)
    answers = await QuizSessionRepository.get_answers_for_session(async_session, row.id)
    answer = next(a for a in answers if a.question_id == "q-multi")
    assert answer.earned == pytest.approx(0.5)
    assert answer.is_correct is False
    assert answer.algorithm == "partial_credit"


@pytest.mark.asyncio
async def test_idempotent_retry_replays_and_does_not_double_record(async_session):
    sid = await _new_session(async_session)
    payload = AnswerSubmit(question_id="q-mcq", selected_answers=[2])

    first = await QuizSessionService.submit_answer(
        async_session, sid, payload, PARTICIPANT, idempotency_key="key-1"
    )
    second = await QuizSessionService.submit_answer(
        async_session, sid, payload, PARTICIPANT, idempotency_key="key-1"
    )
    assert first.model_dump() == second.model_dump()

    row = await QuizSessionRepository.get_by_session_id(async_session, sid)
    answers = await QuizSessionRepository.get_answers_for_session(async_session, row.id)
    assert len(answers) == 1  # not double recorded


@pytest.mark.asyncio
async def test_same_key_different_payload_is_rejected(async_session):
    sid = await _new_session(async_session)
    await QuizSessionService.submit_answer(
        async_session, sid,
        AnswerSubmit(question_id="q-mcq", selected_answers=[2]),
        PARTICIPANT, idempotency_key="key-2",
    )
    with pytest.raises(HTTPException) as exc:
        await QuizSessionService.submit_answer(
            async_session, sid,
            AnswerSubmit(question_id="q-mcq", selected_answers=[3]),
            PARTICIPANT, idempotency_key="key-2",
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_submitted_session_is_immutable(async_session):
    sid = await _new_session(async_session)
    await QuizSessionService.submit_answer(
        async_session, sid,
        AnswerSubmit(question_id="q-mcq", selected_answers=[2]), PARTICIPANT,
    )
    result = await QuizSessionService.submit_session(async_session, sid, PARTICIPANT)
    assert result.status == SessionStatus.submitted.value
    assert result.total_score == 1.0
    assert result.max_score == 3.0

    # No further answers or drafts allowed.
    with pytest.raises(HTTPException) as exc:
        await QuizSessionService.submit_answer(
            async_session, sid,
            AnswerSubmit(question_id="q-tf", selected_answers=[True]), PARTICIPANT,
        )
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc2:
        await QuizSessionService.save_draft(
            async_session, sid, DraftPatch(current_index=1), PARTICIPANT
        )
    assert exc2.value.status_code == 409


@pytest.mark.asyncio
async def test_submit_session_is_idempotent(async_session):
    sid = await _new_session(async_session)
    await QuizSessionService.submit_answer(
        async_session, sid,
        AnswerSubmit(question_id="q-mcq", selected_answers=[2]), PARTICIPANT,
    )
    first = await QuizSessionService.submit_session(async_session, sid, PARTICIPANT)
    second = await QuizSessionService.submit_session(async_session, sid, PARTICIPANT)
    assert first.total_score == second.total_score
    assert second.status == SessionStatus.submitted.value


@pytest.mark.asyncio
async def test_expired_session_rejects_mutation(async_session):
    sid = await _new_session(async_session)
    await _expire(async_session, sid)

    with pytest.raises(HTTPException) as exc:
        await QuizSessionService.submit_answer(
            async_session, sid,
            AnswerSubmit(question_id="q-mcq", selected_answers=[2]), PARTICIPANT,
        )
    assert exc.value.status_code == 409

    # And the session is now flagged expired on read.
    state = await QuizSessionService.get_session(async_session, sid, PARTICIPANT)
    assert state.status == SessionStatus.expired.value


@pytest.mark.asyncio
async def test_draft_autosave_persists_to_session(async_session):
    sid = await _new_session(async_session)
    resp = await QuizSessionService.save_draft(
        async_session, sid,
        DraftPatch(current_index=2, answers={"q-mcq": [2]}), PARTICIPANT,
    )
    assert resp.current_index == 2
    assert resp.draft_answers == {"q-mcq": [2]}

    # Survives a fresh read (server-side, not localStorage).
    state = await QuizSessionService.get_session(async_session, sid, PARTICIPANT)
    assert state.draft_answers == {"q-mcq": [2]}
    assert state.current_index == 2
