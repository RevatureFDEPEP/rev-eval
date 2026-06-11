from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.quiz_session import QuizSession


class QuizSessionRepository:

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> QuizSession:
        session = QuizSession(**kwargs)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_token(db: AsyncSession, token: str) -> QuizSession | None:
        result = await db.execute(
            select(QuizSession).where(QuizSession.session_token == token)
        )
        return result.scalar_one_or_none()
