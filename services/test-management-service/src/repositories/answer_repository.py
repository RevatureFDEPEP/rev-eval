from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.answer import Answer, GradingStatus


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
