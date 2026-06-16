"""W3-F5 — concurrency, idempotency, and the draft version-guard on real Postgres.

Home for invariants only a real Postgres can prove: the ``SELECT FOR UPDATE``
row lock is a no-op on the in-memory SQLite the hermetic suite uses, so the unit
tests check the logic in isolation but never the serialization. These tests
drive the full stack below the gateway — FastAPI app → services → real
question-service over HTTP → the Alembic-migrated integration DB — and cover:
concurrent answer submits (no double-score, backstopped by the unique
constraint), Idempotency-Key replay, draft autosave as a non-scoring no-op, and
the draft version-guard's row lock under a write race.
"""

import asyncio

import pytest
from sqlalchemy import func, select

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.models.session_answer import SessionAnswer

RACE_FANOUT = 5  # matches scripts/smoke-answer-concurrency.sh default N
DRAFT_RACE_FANOUT = 8  # writers per round of the draft version-guard race
DRAFT_RACE_ROUNDS = 5  # independent rounds; compounds detection of a missing
# row lock toward certainty (one 8-way round alone catches it only ~58% of the
# time, since the scheduler often lets the top version commit first).


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
    advancing current_index, or changing status."""
    session_id, question_id = await start_session(3)

    resp = await app_client.patch(
        f"/v1/api/sessions/{session_id}/draft",
        json={"answers": {question_id: [2]}, "client_version": 1},
    )
    assert resp.status_code == 200, resp.text
    ack = resp.json()
    assert ack["current_index"] == 0
    assert ack["status"] == QuizSessionStatus.ACTIVE
    assert ack["applied"] is True
    assert ack["draft_version"] == 1

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
    assert row.draft_version == 1
    assert answer_count == 0  # a draft is never scored


@pytest.mark.asyncio
async def test_concurrent_drafts_version_guard_no_lost_update(
    app_client, start_session, it_db
):
    """A fan-out of racing drafts: the monotonic guard must never lose the
    highest version.

    Unlike the answer path — backstopped by the unique (session_id,
    question_index) constraint — the draft version guard's atomicity rests
    SOLELY on the SELECT FOR UPDATE row lock in ``save_draft`` (a no-op on the
    in-memory SQLite the hermetic suite uses), so only real Postgres exercises
    it. We fire DRAFT_RACE_FANOUT concurrent drafts at one ACTIVE session with
    versions 1..N; the highest carries the winning answers. Each request runs on
    its own connection (app_client's get_db override), so the writes genuinely
    contend: they all read the stored version, then race to commit. The lock
    serialises those read-modify-writes, so the committed state must reflect the
    HIGHEST version regardless of interleaving.

    The fan-out is deliberate: a 2-way race only catches a missing lock ~25% of
    the time (a stale write has to win the commit), whereas N writers all reading
    the pre-write version make a lost update the *likely* outcome without the
    lock — so this reliably fails if the lock regresses, rather than flaking green.
    """
    session_id, question_id = await start_session(3)
    n = DRAFT_RACE_FANOUT
    winner = {question_id: [2]}  # carried only by the highest version, n
    stale = {question_id: [1]}  # every lower version

    def patch(answers, version):
        return app_client.patch(
            f"/v1/api/sessions/{session_id}/draft",
            json={"answers": answers, "client_version": version},
        )

    # Several independent rounds: each fans out versions (base+1 .. base+n) with
    # the top version carrying `winner`. One round catches a broken lock ~58% of
    # the time; compounding rounds drives per-test detection toward certainty,
    # while a working lock passes every round deterministically (no false fails).
    base = 0
    for _ in range(DRAFT_RACE_ROUNDS):
        top = base + n
        responses = await asyncio.gather(
            *(patch(winner if v == top else stale, v) for v in range(base + 1, top + 1))
        )
        # Every draft is accepted (200): a stale draft is a benign no-op.
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]

        async with it_db() as db:
            row = (
                await db.execute(
                    select(QuizSession).where(QuizSession.session_id == session_id)
                )
            ).scalar_one()
        # Invariant to interleaving: the highest version of the round wins and
        # its answers stand; no lower version may clobber it (a lost update).
        assert row.draft_version == top
        assert row.draft_answers == winner
        base = top

    async with it_db() as db:
        answer_count = (
            await db.execute(
                select(func.count())
                .select_from(SessionAnswer)
                .where(SessionAnswer.session_id == session_id)
            )
        ).scalar_one()
    assert row.current_index == 0  # a draft never advances
    assert row.status == QuizSessionStatus.ACTIVE
    assert answer_count == 0  # a draft is never scored
