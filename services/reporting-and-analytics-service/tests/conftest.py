"""Fixtures for the report endpoint tests.

A hermetic aiosqlite in-memory database stands in for test-management's
Postgres: the TmsBase tables are created directly (these are read-only
mappings — only tests ever write them) and `get_tms_db` is overridden so the
app's report queries run against the seeded fixture data.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import main
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt
from src.config.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.db.session import get_tms_db
from src.models.tms_readonly import (
    SessionStatus,
    TmsAnswer,
    TmsBase,
    TmsSession,
    TmsTest,
)

# Deterministic ids so secondary sort (session_id) is predictable.
S1 = UUID(int=1)  # user 42, test 1, SUBMITTED, scores [1.0, 0.5, 0.0] -> 50.0
S2 = UUID(int=2)  # user 42, test 2, SUBMITTED, scores [1.0, 1.0] -> 100.0
S3 = UUID(int=3)  # user 42, test 1, ACTIVE, partial answer (never a score)
S4 = UUID(int=4)  # user 42, test 2, EXPIRED, no answers
S5 = UUID(int=5)  # user 7 noise — must never leak into user 42's reports

USER = 42
OTHER_USER = 7


def _session(sid, test_id, user_id, status, started, expires, submitted=None):
    return TmsSession(
        session_id=sid,
        test_id=test_id,
        user_id=user_id,
        status=status,
        started_at=started,
        expires_at=expires,
        submitted_at=submitted,
        created_at=started,
    )


@pytest.fixture
async def tms_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(TmsBase.metadata.create_all)

    session_factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        db.add_all([
            TmsTest(id=1, name="Java Fundamentals Quiz"),
            TmsTest(id=2, name="Python Data Structures Quiz"),
            _session(S1, 1, USER, SessionStatus.SUBMITTED,
                     datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0),
                     submitted=datetime(2026, 6, 1, 10, 30)),
            _session(S2, 2, USER, SessionStatus.SUBMITTED,
                     datetime(2026, 6, 3, 9, 0), datetime(2026, 6, 3, 10, 0),
                     submitted=datetime(2026, 6, 3, 9, 20)),
            _session(S3, 1, USER, SessionStatus.ACTIVE,
                     datetime(2026, 6, 5, 8, 0), datetime(2026, 6, 5, 9, 0)),
            _session(S4, 2, USER, SessionStatus.EXPIRED,
                     datetime(2026, 5, 20, 14, 0), datetime(2026, 5, 20, 15, 0)),
            _session(S5, 1, OTHER_USER, SessionStatus.SUBMITTED,
                     datetime(2026, 6, 2, 10, 0), datetime(2026, 6, 2, 11, 0),
                     submitted=datetime(2026, 6, 2, 10, 15)),
            # S1: 50% over three questions (qa perfect, qb partial, qc zero)
            TmsAnswer(id=1, session_id=S1, question_id="qa", question_index=0,
                      score=1.0, is_correct=True),
            TmsAnswer(id=2, session_id=S1, question_id="qb", question_index=1,
                      score=0.5, is_correct=False),
            TmsAnswer(id=3, session_id=S1, question_id="qc", question_index=2,
                      score=0.0, is_correct=False),
            # S2: 100% over two questions
            TmsAnswer(id=4, session_id=S2, question_id="qd", question_index=0,
                      score=1.0, is_correct=True),
            TmsAnswer(id=5, session_id=S2, question_id="qe", question_index=1,
                      score=1.0, is_correct=True),
            # S3 is ACTIVE with one partial answer — must never surface a score
            TmsAnswer(id=6, session_id=S3, question_id="qa", question_index=0,
                      score=1.0, is_correct=True),
            # S5: other user's 80% — qa again (different index: random sampling)
            TmsAnswer(id=7, session_id=S5, question_id="qa", question_index=0,
                      score=0.8, is_correct=False),
        ])
        await db.commit()

    yield session_factory

    await engine.dispose()


@pytest.fixture
def make_token():
    """Mint real HS256 tokens against the service's verification settings —
    the require_trainer gate tests verify actual signatures, not mocks."""

    def _make(role="TRAINER", *, secret=None, expires_in=3600, sub="9"):
        payload = {
            "sub": sub,
            "email": "gate-test@example.com",
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }
        return jose_jwt.encode(
            payload, secret or settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    return _make


@pytest.fixture
async def client(tms_db):
    async def _override():
        async with tms_db() as db:
            yield db

    main.app.dependency_overrides[get_tms_db] = _override
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main.app.dependency_overrides.pop(get_tms_db, None)
