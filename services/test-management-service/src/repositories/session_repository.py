import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import Session


class SessionRepository:
    @staticmethod
    async def create(db: AsyncSession, session: Session) -> Session:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id_for_update(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
        result = await db.execute(
            select(Session).where(Session.session_id == session_id).with_for_update()
        )
        return result.scalar_one_or_none()
