from datetime import datetime
from typing import List, Optional

from sqlalchemy import exc as sa_exc
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
        question_ids: Optional[List[str]] = None,
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
            question_ids=question_ids or [],
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
    async def get_locked(db: AsyncSession, session_id: str) -> Optional[Session]:
        """Fetch session with SELECT FOR UPDATE to serialise concurrent answer submissions.

        Falls back to a plain SELECT on databases that do not support FOR UPDATE
        (e.g. SQLite used in tests).
        """
        try:
            result = await db.execute(
                select(Session)
                .where(Session.session_id == session_id)
                .with_for_update()
            )
            return result.scalars().first()
        except (sa_exc.CompileError, Exception) as exc:
            # SQLite raises OperationalError / CompileError for FOR UPDATE
            if "for update" in str(exc).lower() or "not supported" in str(exc).lower():
                result = await db.execute(
                    select(Session).where(Session.session_id == session_id)
                )
                return result.scalars().first()
            raise

    @staticmethod
    async def advance_index(
        db: AsyncSession,
        session: Session,
        new_index: int,
        submitted: bool = False,
    ) -> Session:
        """Advance current_index; optionally mark as SUBMITTED."""
        session.current_index = new_index
        if submitted:
            session.status = SessionStatus.SUBMITTED
            session.submitted_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: int) -> List[Session]:
        result = await db.execute(select(Session).where(Session.user_id == user_id))
        return list(result.scalars().all())

    @staticmethod
    async def list_by_test(db: AsyncSession, test_id: int) -> List[Session]:
        result = await db.execute(select(Session).where(Session.test_id == test_id))
        return list(result.scalars().all())
