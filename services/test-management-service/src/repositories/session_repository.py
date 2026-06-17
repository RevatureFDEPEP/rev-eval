from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import Session


class SessionRepository:
    @staticmethod
    async def create(db: AsyncSession, session: Session) -> Session:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
