from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.session import Session, SessionStatus


class SessionRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: str,
        test_id: int,
        user_id: int,
        session_token: str,
        server_now,
        expires_at,
    ) -> Session:
        session = Session(
            session_id=session_id,
            test_id=test_id,
            user_id=user_id,
            session_token=session_token,
            server_now=server_now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            current_index=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: str) -> Optional[Session]:
        result = await db.execute(select(Session).where(Session.session_id == session_id))
        return result.scalars().first()

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: int) -> List[Session]:
        result = await db.execute(select(Session).where(Session.user_id == user_id))
        return list(result.scalars().all())

    @staticmethod
    async def list_by_test(db: AsyncSession, test_id: int) -> List[Session]:
        result = await db.execute(select(Session).where(Session.test_id == test_id))
        return list(result.scalars().all())
