import os

# Force required settings before `src` is imported so Settings() validates.
# No JWT_SECRET: this service reads the X-User-Role header injected by the
# gateway and never decodes JWTs (platform auth contract).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

from datetime import datetime  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.db.session import Base, get_db  # noqa: E402
from src.models.tms_readonly import (  # noqa: E402
    QuizSession,
    QuizSessionStatus,
    SessionAnswer,
    Test,
)


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 16, hour, minute, 0)


def _seed_objects():
    """Deterministic dataset. User 100 has 4 attempts; user 200 isolates leakage.

    Hand-computed expectations (user 100):
      total_attempts = 4   (all sessions count as attempts)
      per-session scores: s1=2/3, s2=0.75, s4=0.0 (EXPIRED), s3=None (no answers)
      average_score/best_score over SUBMITTED only (s1, s2): mean(2/3, 0.75) = 0.7083,
        best = 0.75. s4 (EXPIRED) and s3 (ACTIVE) are excluded from score stats.
      total_time_spent = 600 (s1) + 300 (s2) = 900   (only SUBMITTED sessions)
      most_recent_attempt = s2 (created 12:00)
    """
    tests = [Test(id=1, name="Python"), Test(id=2, name="SQL")]
    sessions = [
        QuizSession(
            session_id="s1",
            test_id=1,
            user_id=100,
            status=QuizSessionStatus.SUBMITTED,
            created_at=_dt(10, 0),
            started_at=_dt(10, 0),
            submitted_at=_dt(10, 10),
        ),
        QuizSession(
            session_id="s2",
            test_id=2,
            user_id=100,
            status=QuizSessionStatus.SUBMITTED,
            created_at=_dt(12, 0),
            started_at=_dt(11, 0),
            submitted_at=_dt(11, 5),
        ),
        QuizSession(
            session_id="s3",
            test_id=1,
            user_id=100,
            status=QuizSessionStatus.ACTIVE,
            created_at=_dt(11, 0),
            started_at=_dt(11, 0),
            submitted_at=None,
        ),
        QuizSession(
            session_id="s4",
            test_id=1,
            user_id=100,
            status=QuizSessionStatus.EXPIRED,
            created_at=_dt(10, 30),
            started_at=_dt(12, 0),
            submitted_at=None,
        ),
        QuizSession(
            session_id="s9",
            test_id=1,
            user_id=200,
            status=QuizSessionStatus.SUBMITTED,
            created_at=_dt(9, 0),
            started_at=_dt(9, 0),
            submitted_at=_dt(9, 30),
        ),
    ]
    answers = [
        SessionAnswer(
            session_id="s1", is_correct=True, points_earned=1.0, max_points=1.0
        ),
        SessionAnswer(
            session_id="s1", is_correct=True, points_earned=1.0, max_points=1.0
        ),
        SessionAnswer(
            session_id="s1", is_correct=False, points_earned=0.0, max_points=1.0
        ),
        SessionAnswer(
            session_id="s2", is_correct=True, points_earned=1.0, max_points=1.0
        ),
        SessionAnswer(
            session_id="s2", is_correct=False, points_earned=0.5, max_points=1.0
        ),
        SessionAnswer(
            session_id="s4", is_correct=False, points_earned=0.0, max_points=1.0
        ),
        SessionAnswer(
            session_id="s9", is_correct=True, points_earned=1.0, max_points=1.0
        ),
    ]
    return tests + sessions + answers


@pytest_asyncio.fixture
async def engine():
    """Shared in-memory SQLite (StaticPool → one connection → one DB), seeded."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        s.add_all(_seed_objects())
        await s.commit()
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine):
    """httpx client over the ASGI app, with get_db pointed at the seeded engine."""
    from main import app

    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
