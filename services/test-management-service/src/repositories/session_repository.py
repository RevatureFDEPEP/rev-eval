# src/repositories/session_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.session import QuizSession


class SessionRepository:

    @staticmethod
    async def create(db: AsyncSession, session: QuizSession) -> QuizSession:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: str) -> QuizSession | None:
        result = await db.execute(
            select(QuizSession).where(QuizSession.session_id == session_id)
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, session: QuizSession, data: dict) -> QuizSession:
        for field, value in data.items():
            setattr(session, field, value)
        await db.commit()
        await db.refresh(session)
        return session
