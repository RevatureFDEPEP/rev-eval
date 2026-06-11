# src/repositories/quiz_session_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.models.quiz_session import QuizSession


class QuizSessionRepository:

    @staticmethod
    async def create(db: AsyncSession, session: QuizSession) -> QuizSession:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: str) -> Optional[QuizSession]:
        result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id_for_update(db: AsyncSession, session_id: str) -> Optional[QuizSession]:
        """Pessimistic lock -- blocks concurrent submits on same session row."""
        result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id).with_for_update()
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_submission_id(db: AsyncSession, submission_id: int) -> Optional[QuizSession]:
        result = await db.execute(
            select(QuizSession).where(QuizSession.submission_id == submission_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def save(db: AsyncSession, session: QuizSession) -> QuizSession:
        await db.commit()
        await db.refresh(session)
        return session
