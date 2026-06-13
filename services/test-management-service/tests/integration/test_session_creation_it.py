"""W3-F5 — session-creation happy path against real Postgres + Mongo.

Codifies the F1 happy-path smoke (docs/internal/docs/plans/w3-f1-smoke-test.sh)
as a deterministic, seeded pytest integration test. The POST goes through the
real stack below the gateway: FastAPI app → QuizSessionService → httpx →
question-management-service → Mongo ``$sample``, with the session row persisted
to the Alembic-migrated integration database.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.models.quiz_session import QuizSession, QuizSessionStatus

DURATION = timedelta(minutes=30)


@pytest.mark.asyncio
async def test_create_session_persists_server_authoritative_timing(
    app_client, seed_quiz, it_db
):
    quiz = await seed_quiz(n=3, duration=DURATION)

    # Naive UTC to match the server's datetime.now(UTC).replace(tzinfo=None).
    before = datetime.now(UTC).replace(tzinfo=None)
    resp = await app_client.post("/v1/api/sessions", json={"test_id": quiz["test_id"]})
    after = datetime.now(UTC).replace(tzinfo=None)

    assert resp.status_code == 201, resp.text
    body = resp.json()

    # A parseable UUID — uuid.UUID raises on anything malformed.
    session_id = str(uuid.UUID(body["session_id"]))

    assert body["current_index"] == 0
    assert body["total_questions"] == 3
    question = body["question"]
    assert question is not None and question["question_text"]
    assert question["index"] == 0
    # The answer key must never reach the candidate.
    assert "correct_answers" not in question
    assert "sample_answer" not in question

    # Timing is server-authoritative: expires_at == server_now + duration, and
    # server_now lands within a ±1s tolerance of the wall clock around the call.
    server_now = datetime.fromisoformat(body["server_now"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at - server_now == DURATION
    assert before - timedelta(seconds=1) <= server_now <= after + timedelta(seconds=1)

    # The session row was persisted with the frozen question set and ACTIVE state.
    async with it_db() as db:
        row = (
            await db.execute(
                select(QuizSession).where(QuizSession.session_id == session_id)
            )
        ).scalar_one()
    assert row.status == QuizSessionStatus.ACTIVE
    assert row.current_index == 0
    assert len(row.question_ids) == 3
    assert row.expires_at == expires_at


@pytest.mark.asyncio
async def test_create_session_unknown_test_404(app_client, seed_quiz):
    # Seed a quiz so the question bank is non-empty, then request a bogus id.
    await seed_quiz(n=1)
    resp = await app_client.post("/v1/api/sessions", json={"test_id": 99_999_999})
    assert resp.status_code == 404, resp.text
