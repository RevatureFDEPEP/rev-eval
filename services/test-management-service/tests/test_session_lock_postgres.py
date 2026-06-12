"""
tests/test_session_lock_postgres.py

Proves that QuizSessionRepository.get_by_id_for_update serializes concurrent
transactions via Postgres SELECT FOR UPDATE.

SQLite serializes at the file level and ignores WITH FOR UPDATE, so the same
test against SQLite would pass trivially without proving anything about locking.
This test only runs in CI where the Postgres service container is available.
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Env vars must be set before any src.* import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mgmt.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

from src.db.session import Base
from src.models.quiz_session import QuizSession, SessionStatus  # noqa: F401
from src.models.test import Test, TestType  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401
from src.repositories.quiz_session_repository import QuizSessionRepository

_PG_URL = "postgresql+asyncpg://test:test@localhost:5432/test"

_IN_CI = os.environ.get("CI") == "true"


def _make_engine():
    return create_async_engine(_PG_URL, poolclass=NullPool)


async def _bootstrap_schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_parents(factory):
    """Insert Test(id=1) and TestSubmission(id=1) so FK constraints are satisfied."""
    async with factory() as db:
        test = Test(id=1, name="Lock Test", test_type=TestType.QUIZ)
        db.add(test)
        await db.flush()
        sub = TestSubmission(id=1, test_id=1, user_id=1)
        db.add(sub)
        await db.commit()


async def _seed_session(factory, session_id: str):
    await _seed_parents(factory)
    async with factory() as db:
        row = QuizSession(
            id=session_id,
            token_hash="testhash",
            test_id=1,
            submission_id=1,
            user_id=1,
            status=SessionStatus.PART_A_IN_PROGRESS,
            server_now=datetime.utcnow(),
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2),
            total_questions=10,
            part_a_config={"easy": 3, "medium": 4, "hard": 3},
            part_b_config={"easy": 3, "medium": 4, "hard": 3},
        )
        db.add(row)
        await db.commit()


@pytest.mark.skipif(not _IN_CI, reason="Requires Postgres service container — CI only")
def test_for_update_serializes_concurrent_writers():
    """
    Two transactions both call get_by_id_for_update on the same row.
    tx1 acquires the lock, sleeps 100ms, updates status, then commits.
    tx2 starts 50ms later and blocks on the lock until tx1 commits.
    After tx2 unblocks it must observe the status written by tx1,
    proving the lock serialized the two writers rather than interleaving them.
    """

    async def _run():
        engine = _make_engine()
        await _bootstrap_schema(engine)

        factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session_id = str(uuid.uuid4())
        await _seed_session(factory, session_id)

        order: list[str] = []

        async def tx1():
            async with factory() as db:
                row = await QuizSessionRepository.get_by_id_for_update(db, session_id)
                order.append("tx1_locked")
                await asyncio.sleep(0.1)  # hold the lock
                row.status = SessionStatus.PART_A_COMPLETED
                await db.commit()
                order.append("tx1_committed")

        async def tx2():
            await asyncio.sleep(0.05)  # ensure tx1 acquires the lock first
            async with factory() as db:
                row = await QuizSessionRepository.get_by_id_for_update(db, session_id)
                # tx2 only reaches here after tx1 has committed
                order.append("tx2_locked")
                assert row.status == SessionStatus.PART_A_COMPLETED

        await asyncio.gather(tx1(), tx2())

        # tx1 must have committed before tx2 acquired the lock
        assert "tx1_committed" in order
        assert "tx2_locked" in order
        assert order.index("tx1_committed") < order.index("tx2_locked"), (
            "tx2 acquired the lock before tx1 committed — FOR UPDATE did not serialize"
        )

        await engine.dispose()

    asyncio.run(_run())
