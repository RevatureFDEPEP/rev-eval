"""W3-F5 steps 3–4 — pessimistic locking and idempotency on real Postgres.

The unit suite proves the scoring math; only a real Postgres can prove the
``SELECT FOR UPDATE`` race behavior these tests pin down. Both tests drive the
full request path (FastAPI → SessionService → real question-service for the
answer key → the migrated integration DB).
"""
import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from src.models.answer import Answer
from src.models.idempotency_key import IdempotencyKey
from src.models.session import Session, SessionStatus

pytestmark = pytest.mark.integration

ANSWER = {"submitted_answers": [2]}


async def _start_session(app_client, make_test, mongo_questions, n_questions):
    mongo_questions(n=max(n_questions, 1))
    test = await make_test(
        number_of_questions=n_questions, duration=timedelta(minutes=30)
    )
    resp = await app_client.post("/v1/api/sessions/", json={"test_id": test.id})
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["session_id"])


async def test_concurrent_answers_serialize_one_200_one_409(
    app_client, make_test, mongo_questions, it_db
):
    """Two concurrent submissions of the same answer to the same session.

    A single-question session makes the race outcome observable through the
    state machine: whichever request wins the ``FOR UPDATE`` lock scores
    question 0 and finalizes the session to SUBMITTED; the loser queues on the
    row lock and then hits the terminal-state gate → 409. Without the lock,
    both would read current_index=0 and double-score.
    """
    session_id = await _start_session(app_client, make_test, mongo_questions, 1)

    def post(key):
        return app_client.post(
            f"/v1/api/sessions/{session_id}/answer",
            json=ANSWER,
            headers={"Idempotency-Key": key},
        )

    # Different keys on purpose: this exercises the lock, not the dedup table.
    resp_a, resp_b = await asyncio.gather(post("race-key-a"), post("race-key-b"))

    codes = sorted([resp_a.status_code, resp_b.status_code])
    assert codes == [200, 409], (resp_a.text, resp_b.text)

    async with it_db() as db:
        row = (
            await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
        ).scalar_one()
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(Answer)
                .where(Answer.session_id == session_id)
            )
        ).scalar_one()

    # Advanced exactly once, by exactly one scored answer.
    assert row.current_index == 1
    assert row.status == SessionStatus.SUBMITTED
    assert answer_count == 1


async def test_same_idempotency_key_mutates_session_exactly_once(
    app_client, make_test, mongo_questions, it_db
):
    """The same answer posted twice with the same Idempotency-Key.

    The second request must replay the stored response (identical body, no
    re-scoring) and leave the session row, answers, and dedup table exactly as
    the first request left them.
    """
    session_id = await _start_session(app_client, make_test, mongo_questions, 3)

    def post():
        return app_client.post(
            f"/v1/api/sessions/{session_id}/answer",
            json=ANSWER,
            headers={"Idempotency-Key": "retry-key-1"},
        )

    first = await post()
    second = await post()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()

    async with it_db() as db:
        row = (
            await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
        ).scalar_one()
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(Answer)
                .where(Answer.session_id == session_id)
            )
        ).scalar_one()
        key_count = (
            await db.execute(
                select(func.count())
                .select_from(IdempotencyKey)
                .where(IdempotencyKey.session_id == session_id)
            )
        ).scalar_one()

    assert row.current_index == 1  # mutated exactly once
    assert row.status == SessionStatus.ACTIVE  # 2 of 3 questions remain
    assert answer_count == 1
    assert key_count == 1
