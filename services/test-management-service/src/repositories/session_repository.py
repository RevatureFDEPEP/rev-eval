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
    async def get_by_id_for_update(
        db: AsyncSession, session_id: str
    ) -> QuizSession | None:
        """Load the session row with a ``SELECT ... FOR UPDATE`` row lock so
        concurrent answer submissions queue instead of racing on
        ``current_index`` (W3-F2 pessimistic locking). Must run inside an open
        transaction; the lock is held until commit/rollback."""
        result = await db.execute(
            select(QuizSession)
            .where(QuizSession.session_id == session_id)
            .with_for_update()
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, session: QuizSession, data: dict) -> QuizSession:
        for field, value in data.items():
            setattr(session, field, value)
        await db.commit()
        await db.refresh(session)
        return session
