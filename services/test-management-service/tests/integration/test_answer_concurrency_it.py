"""W3-F5 — pessimistic locking + idempotency on real Postgres.

The pytest port of ``scripts/smoke-answer-concurrency.sh``, wiring its four
invariants into CI. The unit suite proves the scoring math; only a real
Postgres can prove the ``SELECT FOR UPDATE`` race behaviour (a no-op on the
in-memory SQLite the hermetic suite uses). Both tests drive the full request
path: FastAPI → QuizSessionScoringService → real question-service for the
answer key → the migrated integration DB.
"""

import asyncio

import pytest
from sqlalchemy import func, select

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.models.session_answer import SessionAnswer

RACE_FANOUT = 5  # matches scripts/smoke-answer-concurrency.sh default N


@pytest.mark.asyncio
async def test_concurrent_answers_score_exactly_once(app_client, start_session, it_db):
    """N concurrent submits of the same answer must never double-score.

    Single-question session, so the race outcome is observable through the
    state machine: whichever request wins the ``FOR UPDATE`` lock scores
    question 0 and finalises the session to SUBMITTED; the others queue on the
    row lock, then hit the terminal-state gate (or the unique
    ``(session_id, question_index)`` constraint) → 409. Without the lock they
    would all read current_index=0 and double-score.
    """
    session_id, question_id = await start_session(1)

    def post(key: str):
        return app_client.post(
            f"/v1/api/sessions/{session_id}/answer",
            json={"question_id": question_id, "submitted_answers": [2]},
            headers={"Idempotency-Key": key},
        )

    # Distinct keys on purpose: this exercises the lock, not the dedup column.
    responses = await asyncio.gather(
        *(post(f"race-key-{i}") for i in range(RACE_FANOUT))
    )
    codes = sorted(r.status_code for r in responses)

    assert codes.count(200) == 1, [r.text for r in responses]
    assert codes.count(409) == RACE_FANOUT - 1, [r.text for r in responses]

    async with it_db() as db:
        row = (
            await db.execute(
                select(QuizSession).where(QuizSession.session_id == session_id)
            )
        ).scalar_one()
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(SessionAnswer)
                .where(SessionAnswer.session_id == session_id)
            )
        ).scalar_one()
        dup_index_rows = (
            await db.execute(
                select(func.count()).select_from(
                    select(SessionAnswer.question_index)
                    .where(SessionAnswer.session_id == session_id)
                    .group_by(SessionAnswer.question_index)
                    .having(func.count() > 1)
                    .subquery()
                )
            )
        ).scalar_one()

    # Advanced exactly once, by exactly one scored answer, no duplicate index.
    assert answer_count == 1
    assert dup_index_rows == 0
    assert row.current_index == 1
    assert row.status == QuizSessionStatus.SUBMITTED


@pytest.mark.asyncio
async def test_same_idempotency_key_mutates_session_exactly_once(
    app_client, start_session, it_db
):
    """The same answer posted twice with the same Idempotency-Key.

    The second request replays the stored result (identical body, no
    re-scoring) and leaves the session row and answers exactly as the first
    left them. Three questions, so the session stays ACTIVE after question 0.
    """
    session_id, question_id = await start_session(3)
    body = {"question_id": question_id, "submitted_answers": [2]}
    headers = {"Idempotency-Key": "retry-key-1"}

    first = await app_client.post(
        f"/v1/api/sessions/{session_id}/answer", json=body, headers=headers
    )
    second = await app_client.post(
        f"/v1/api/sessions/{session_id}/answer", json=body, headers=headers
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()

    async with it_db() as db:
        row = (
            await db.execute(
                select(QuizSession).where(QuizSession.session_id == session_id)
            )
        ).scalar_one()
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(SessionAnswer)
                .where(SessionAnswer.session_id == session_id)
            )
        ).scalar_one()

    assert answer_count == 1  # mutated exactly once
    assert row.current_index == 1
    assert row.status == QuizSessionStatus.ACTIVE  # 2 of 3 questions remain


@pytest.mark.asyncio
async def test_draft_persists_without_advancing(app_client, start_session, it_db):
    """W3-F4 surface: PATCH /draft persists the answer map without scoring,
    advancing current_index, or changing status (last-write-wins)."""
    session_id, question_id = await start_session(3)

    resp = await app_client.patch(
        f"/v1/api/sessions/{session_id}/draft",
        json={"answers": {question_id: [2]}},
    )
    assert resp.status_code == 200, resp.text
    ack = resp.json()
    assert ack["current_index"] == 0
    assert ack["status"] == QuizSessionStatus.ACTIVE

    async with it_db() as db:
        row = (
            await db.execute(
                select(QuizSession).where(QuizSession.session_id == session_id)
            )
        ).scalar_one()
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(SessionAnswer)
                .where(SessionAnswer.session_id == session_id)
            )
        ).scalar_one()

    assert row.current_index == 0
    assert row.status == QuizSessionStatus.ACTIVE
    assert row.draft_answers == {question_id: [2]}
    assert answer_count == 0  # a draft is never scored
