"""W3-F5 step 2 — session-creation happy path against real Postgres + Mongo.

The POST goes through the real stack below the gateway: FastAPI app →
SessionService → httpx → question-management-service → Mongo ``$sample``,
with the session row persisted to the Alembic-migrated integration database.
"""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from src.models.session import Session, SessionStatus

pytestmark = pytest.mark.integration

DURATION = timedelta(minutes=30)


async def test_create_session_persists_server_authoritative_timing(
    app_client, make_test, mongo_questions, it_db
):
    mongo_questions(n=3)
    test = await make_test(number_of_questions=3, duration=DURATION)

    before = datetime.utcnow()
    resp = await app_client.post("/v1/api/sessions/", json={"test_id": test.id})
    after = datetime.utcnow()

    assert resp.status_code == 201, resp.text
    body = resp.json()

    # A parseable UUID — uuid.UUID raises on anything malformed.
    session_id = uuid.UUID(body["session_id"])

    assert body["current_index"] == 0
    assert body["total_questions"] == 3
    question = body["question"]
    assert question is not None and question["question_text"]
    # The answer key must never reach the candidate.
    assert "correct_answers" not in question
    assert "sample_answer" not in question

    async with it_db() as db:
        row = (
            await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
        ).scalar_one()

    assert row.status == SessionStatus.ACTIVE
    assert row.current_index == 0
    assert len(row.question_ids) == 3

    # Server-computed: expires_at is exactly server_now + test.duration …
    assert row.expires_at == row.server_now + DURATION
    # … and lands at now + duration within the spec's ±1s tolerance.
    assert before + DURATION - timedelta(seconds=1) <= row.expires_at
    assert row.expires_at <= after + DURATION + timedelta(seconds=1)


async def test_create_session_unknown_test_404(app_client, mongo_questions):
    mongo_questions(n=1)
    resp = await app_client.post("/v1/api/sessions/", json={"test_id": 99_999_999})
    assert resp.status_code == 404
