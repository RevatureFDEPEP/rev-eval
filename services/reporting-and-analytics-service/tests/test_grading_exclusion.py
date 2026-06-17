"""PENDING_REVIEW answers are excluded from the attempt score (W5-F1).

A free-text answer awaiting a manual grade must not drag the attempt's
on-read AVG to 0; once graded it counts. Exercised at the repository layer
against a hermetic sqlite copy of the TMS read-only tables.
"""
from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.models.tms_readonly import (
    GradingStatus,
    SessionStatus,
    TmsAnswer,
    TmsBase,
    TmsSession,
    TmsTest,
)
from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import AttemptsQuery

USER = 42
SID = UUID(int=10)


async def _seed(pending_status, pending_score):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(TmsBase.metadata.create_all)
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add_all([
            TmsTest(id=1, name="Quiz"),
            TmsSession(
                session_id=SID, test_id=1, user_id=USER,
                status=SessionStatus.SUBMITTED,
                started_at=datetime(2026, 6, 1, 10, 0),
                expires_at=datetime(2026, 6, 1, 11, 0),
                submitted_at=datetime(2026, 6, 1, 10, 30),
                created_at=datetime(2026, 6, 1, 10, 0),
                needs_grading=(pending_status == GradingStatus.PENDING_REVIEW),
            ),
            # One auto-scored perfect answer.
            TmsAnswer(id=1, session_id=SID, question_id="qa", question_index=0,
                      score=1.0, is_correct=True, grading_status=GradingStatus.AUTO),
            # One free-text answer — pending or graded.
            TmsAnswer(id=2, session_id=SID, question_id="qt", question_index=1,
                      score=pending_score, is_correct=False,
                      grading_status=pending_status),
        ])
        await db.commit()
    return engine, factory


@pytest.mark.asyncio
async def test_pending_answer_excluded_then_counted_when_graded():
    # Pending: only the auto answer (1.0) counts -> 100%, flagged needs_grading.
    engine, factory = await _seed(GradingStatus.PENDING_REVIEW, 0.0)
    async with factory() as db:
        rows, total = await ReportRepository.user_attempts(
            db, USER, AttemptsQuery()
        )
    assert total == 1
    assert rows[0].score == pytest.approx(100.0)
    assert bool(rows[0].needs_grading) is True
    await engine.dispose()

    # Graded 0.5: both answers count -> AVG(1.0, 0.5)*100 = 75%.
    engine, factory = await _seed(GradingStatus.GRADED, 0.5)
    async with factory() as db:
        rows, _ = await ReportRepository.user_attempts(db, USER, AttemptsQuery())
    assert rows[0].score == pytest.approx(75.0)
    assert bool(rows[0].needs_grading) is False
    await engine.dispose()
