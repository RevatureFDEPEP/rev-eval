from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.session import Session
from src.models.test import Test


class SessionRepository:

    @staticmethod
    async def get_test(db: AsyncSession, test_id: int) -> Optional[Test]:
        """Fetch the raw Test model (for duration/number_of_questions).

        Direct select rather than TestRepository.get_by_id, which crashes on
        a missing id (sets an attribute on None) — see W3-F1 plan defect note.
        """
        result = await db.execute(select(Test).where(Test.id == test_id))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, session: Session) -> Session:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: UUID) -> Optional[Session]:
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_token(db: AsyncSession, session_token: str) -> Optional[Session]:
        result = await db.execute(
            select(Session).where(Session.session_token == session_token)
        )
        return result.scalars().first()

    @staticmethod
    async def get_for_update(
        db: AsyncSession, session_id: UUID
    ) -> Optional[Session]:
        """Fetch a session row with a pessimistic ``SELECT ... FOR UPDATE`` lock.

        Must run inside the caller's open transaction (the answer endpoint owns
        the transaction). Concurrent submissions for the same session serialize
        on this lock rather than racing the read-modify-write of current_index.
        (On SQLite the lock clause is a no-op, which is fine for unit tests.)
        """
        result = await db.execute(
            select(Session).where(Session.session_id == session_id).with_for_update()
        )
        return result.scalars().first()

    @staticmethod
    async def flush(db: AsyncSession, session: Session) -> Session:
        """Stage session mutations without committing — the endpoint commits
        the whole transaction once at the end."""
        db.add(session)
        await db.flush()
        return session
