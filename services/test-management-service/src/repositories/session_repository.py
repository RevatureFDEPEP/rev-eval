from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.test_session import TestSession


class SessionRepository:

    @staticmethod
    async def create(db: AsyncSession, session: TestSession) -> TestSession:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_token(db: AsyncSession, token: str) -> TestSession | None:
        result = await db.execute(
            select(TestSession).where(TestSession.token == token)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_submission_id(db: AsyncSession, submission_id: int) -> TestSession | None:
        result = await db.execute(
            select(TestSession)
            .where(TestSession.submission_id == submission_id)
            .order_by(TestSession.created_at.desc())
        )
        return result.scalars().first()
