"""W3-F5 — state-machine failure paths against real Postgres.

Failure-injection coverage for the guards W3-F4 hardened (idempotency-before-
status, expire-and-lock, draft-on-terminal). These depend on real persisted
session state across requests, so the hermetic SQLite suite can't exercise them
end to end. Complements the happy-path idempotency/race coverage in
test_answer_concurrency_it.py.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.models.session_answer import SessionAnswer


def _answer(app_client, session_id, question_id, key):
    return app_client.post(
        f"/v1/api/sessions/{session_id}/answer",
        json={"question_id": question_id, "submitted_answers": [2]},
        headers={"Idempotency-Key": key},
    )


@pytest.mark.asyncio
async def test_final_answer_replayable_after_submit(app_client, start_session, it_db):
    """A retried submit of the FINAL answer must replay its cached result even
    after the session is SUBMITTED — the idempotency lookup runs before the
    terminal-state guard, so the last answer is never lost to a 409 on retry.
    """
    session_id, question_id = await start_session(1)
    key = "final-answer-key"

    first = await _answer(app_client, session_id, question_id, key)
    assert first.status_code == 200, first.text
    assert first.json()["session_status"] == QuizSessionStatus.SUBMITTED

    # Same key again, now that the session is terminal: cached replay, not 409.
    replay = await _answer(app_client, session_id, question_id, key)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()

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

    assert answer_count == 1  # the replay did not re-score
    assert row.status == QuizSessionStatus.SUBMITTED


@pytest.mark.asyncio
async def test_expired_session_rejects_answer_without_scoring(
    app_client, start_session, it_db
):
    """An answer submitted after the timer has elapsed is rejected with 409 and
    is NOT scored; the lazy guard flips the session to EXPIRED first."""
    session_id, question_id = await start_session(1)

    # Backdate the deadline so the next answer arrives past expiry.
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    async with it_db() as db:
        await db.execute(
            update(QuizSession)
            .where(QuizSession.session_id == session_id)
            .values(expires_at=past)
        )
        await db.commit()

    resp = await _answer(app_client, session_id, question_id, "post-expiry-key")
    assert resp.status_code == 409, resp.text
    assert "expired" in resp.json()["detail"].lower()

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

    assert row.status == QuizSessionStatus.EXPIRED  # lazy expiry persisted
    assert answer_count == 0  # the in-flight answer was never scored


@pytest.mark.asyncio
async def test_draft_rejected_on_terminal_session(app_client, start_session, it_db):
    """Autosave must not write to a finished attempt: PATCH /draft on a
    SUBMITTED session is rejected with 409 and leaves draft_answers untouched."""
    session_id, question_id = await start_session(1)

    submitted = await _answer(app_client, session_id, question_id, "submit-key")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["session_status"] == QuizSessionStatus.SUBMITTED

    resp = await app_client.patch(
        f"/v1/api/sessions/{session_id}/draft",
        json={"answers": {question_id: [1]}},
    )
    assert resp.status_code == 409, resp.text

    async with it_db() as db:
        row = (
            await db.execute(
                select(QuizSession).where(QuizSession.session_id == session_id)
            )
        ).scalar_one()
    assert row.status == QuizSessionStatus.SUBMITTED
    assert row.draft_answers is None  # the rejected draft did not persist
