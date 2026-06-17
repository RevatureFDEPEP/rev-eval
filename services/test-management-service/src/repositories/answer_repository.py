from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.answer import Answer, GradingStatus
from src.models.session import Session
from src.models.test import Test


class AnswerRepository:

    @staticmethod
    async def create(db: AsyncSession, answer: Answer) -> Answer:
        """Stage a scored answer row. The answer endpoint owns the transaction
        and commits once at the end, so this flushes rather than commits."""
        db.add(answer)
        await db.flush()
        return answer

    @staticmethod
    async def count_pending(db: AsyncSession, session_id: UUID) -> int:
        """Count answers in a session still awaiting a manual grade (W5-F1)."""
        result = await db.execute(
            select(func.count(Answer.id)).where(
                Answer.session_id == session_id,
                Answer.grading_status == GradingStatus.PENDING_REVIEW,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def get(db: AsyncSession, answer_id: int) -> Answer | None:
        """Load one answer by id."""
        result = await db.execute(select(Answer).where(Answer.id == answer_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slot(
        db: AsyncSession, session_id: UUID, question_index: int
    ) -> Answer | None:
        """Load the answer at a session's question slot (W5-F1 grade target)."""
        result = await db.execute(
            select(Answer).where(
                Answer.session_id == session_id,
                Answer.question_index == question_index,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_pending(
        db: AsyncSession,
        *,
        test_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Tuple[Answer, int, int, "datetime", Optional[str]]], int]:
        """Page through PENDING_REVIEW answers, joined to session + test for
        the trainer queue. Returns (rows, total) where each row is
        (Answer, session_user_id, test_id, submitted_at, test_name)."""
        cols = (
            Answer,
            Session.user_id,
            Session.test_id,
            Session.submitted_at,
            Test.name,
        )
        base = (
            select(*cols)
            .join(Session, Session.session_id == Answer.session_id)
            .join(Test, Test.id == Session.test_id)
            .where(Answer.grading_status == GradingStatus.PENDING_REVIEW)
        )
        count_q = (
            select(func.count(Answer.id))
            .join(Session, Session.session_id == Answer.session_id)
            .where(Answer.grading_status == GradingStatus.PENDING_REVIEW)
        )
        if test_id is not None:
            base = base.where(Session.test_id == test_id)
            count_q = count_q.where(Session.test_id == test_id)

        total = int((await db.execute(count_q)).scalar_one())
        rows = (
            await db.execute(
                base.order_by(Answer.created_at.asc())
                .offset((page - 1) * size)
                .limit(size)
            )
        ).all()
        return list(rows), total
