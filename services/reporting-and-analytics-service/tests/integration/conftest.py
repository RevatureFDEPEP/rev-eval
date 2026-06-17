"""Fixtures for the cross-schema integration suite — real Postgres, no mocks.

Prerequisite containers (from the repo root):

    docker compose up -d --wait postgres test-management-service

What "real" means here: the schema under test is **test-management-service's**,
created by *its* Alembic migrations on startup (including the native
``quizsessionstatus`` enum). We seed rows with raw SQL straight into those real
tables — never via reporting's ``tms_readonly`` mirror — so a column rename or a
dropped constraint surfaces as a failed insert/select rather than passing
against a mirror that quietly drifted. Reporting's queries then run against that
real schema and we assert the hand-computed numbers.

Connection knob (default matches the published docker-compose host port):

    IT_DATABASE_URL   postgresql+asyncpg://root:root@localhost:5432/eval_ai_dev

Isolation: a high, unlikely-to-collide user id; every seeded row is removed in
teardown, with a defensive delete-by-user-id sweep for orphans from a crashed run.
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

IT_DATABASE_URL = os.getenv(
    "IT_DATABASE_URL", "postgresql+asyncpg://root:root@localhost:5432/eval_ai_dev"
)

# Isolated identifiers for this suite.
IT_USER_ID = 9990001
IT_TEST_ID = 990001
IT_SESSIONS = ("it_rs1", "it_rs2")


@pytest_asyncio.fixture(scope="session")
async def real_engine():
    """Async engine on the test-management-migrated Postgres; skip if absent."""
    engine = create_async_engine(IT_DATABASE_URL, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            present = await conn.scalar(
                text("SELECT to_regclass('public.quiz_sessions')")
            )
    except Exception as e:  # connection refused, auth, etc.
        await engine.dispose()
        pytest.skip(f"Postgres not reachable at {IT_DATABASE_URL}: {e}")
    if present is None:
        await engine.dispose()
        pytest.skip(
            "quiz_sessions not found — start test-management-service so it "
            "migrates the schema (docker compose up -d --wait postgres "
            "test-management-service)"
        )
    yield engine
    await engine.dispose()


async def _cleanup(conn) -> None:
    await conn.execute(
        text("DELETE FROM session_answers WHERE session_id = ANY(:ids)"),
        {"ids": list(IT_SESSIONS)},
    )
    await conn.execute(
        text("DELETE FROM quiz_sessions WHERE user_id = :uid"), {"uid": IT_USER_ID}
    )
    await conn.execute(text("DELETE FROM tests WHERE id = :tid"), {"tid": IT_TEST_ID})


@pytest_asyncio.fixture
async def seeded_real(real_engine):
    """Seed the deterministic dataset into the real tables; yield ids; clean up.

    Hand-computed (user 9990001): total_attempts=2; it_rs1 SUBMITTED score 0.5
    (1/2 answers, 600s), it_rs2 ACTIVE no answers; average=best=0.5; time=600;
    most_recent=it_rs2 (created 11:00).
    """
    async with real_engine.begin() as conn:
        await _cleanup(conn)  # clear any orphan from a crashed prior run
        await conn.execute(
            text(
                "INSERT INTO tests (id, name, test_type, active) "
                "VALUES (:id, 'IT Reporting Test', 'QUIZ', true)"
            ),
            {"id": IT_TEST_ID},
        )
        await conn.execute(
            text(
                "INSERT INTO quiz_sessions "
                "(session_id, test_id, user_id, session_token, question_ids, "
                " current_index, draft_version, status, created_at, started_at, "
                " expires_at, submitted_at) VALUES "
                "('it_rs1', :tid, :uid, 'it-tok-1', '[\"q1\",\"q2\"]', 2, 0, "
                " 'SUBMITTED', '2026-06-16 10:00', '2026-06-16 10:00', "
                " '2026-06-16 10:30', '2026-06-16 10:10'),"
                "('it_rs2', :tid, :uid, 'it-tok-2', '[\"q1\",\"q2\"]', 1, 0, "
                " 'ACTIVE', '2026-06-16 11:00', '2026-06-16 11:00', "
                " '2026-06-16 11:30', NULL)"
            ),
            {"tid": IT_TEST_ID, "uid": IT_USER_ID},
        )
        await conn.execute(
            text(
                "INSERT INTO session_answers "
                "(session_id, question_id, question_index, submitted_answers, "
                " is_correct, points_earned, max_points, requires_manual_review, "
                " idempotency_key) VALUES "
                "('it_rs1','q1',0,'[0]', true, 1.0, 1.0, false, 'it-idk-0'),"
                "('it_rs1','q2',1,'[1]', false,0.0, 1.0, false, 'it-idk-1')"
            )
        )
    yield {"user_id": IT_USER_ID, "test_id": IT_TEST_ID}
    async with real_engine.begin() as conn:
        await _cleanup(conn)


@pytest_asyncio.fixture
async def real_session(real_engine) -> AsyncSession:
    factory = sessionmaker(
        bind=real_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as s:
        yield s
