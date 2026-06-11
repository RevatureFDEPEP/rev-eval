from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.quiz_session import QuizSession, QuizSessionQuestion, SessionStatus


class QuizSessionRepository:

    @staticmethod
    async def create(db: AsyncSession, session: QuizSession) -> QuizSession:
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def count_active_for_user(db: AsyncSession, user_id: int) -> int:
        """Count in-progress sessions for a user (anti-abuse guard)."""
        result = await db.execute(
            select(func.count())
            .select_from(QuizSession)
            .where(
                QuizSession.user_id == user_id,
                QuizSession.status == SessionStatus.in_progress,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def add_question(db: AsyncSession, question: QuizSessionQuestion) -> None:
        db.add(question)

    @staticmethod
    async def get_by_session_id(db: AsyncSession, session_id) -> Optional[QuizSession]:
        result = await db.execute(
            select(QuizSession).where(QuizSession.session_id == session_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_questions_for_session(
        db: AsyncSession, quiz_session_id: int
    ) -> List[QuizSessionQuestion]:
        result = await db.execute(
            select(QuizSessionQuestion)
            .where(QuizSessionQuestion.quiz_session_id == quiz_session_id)
            .order_by(QuizSessionQuestion.question_index)
        )
        return list(result.scalars().all())
