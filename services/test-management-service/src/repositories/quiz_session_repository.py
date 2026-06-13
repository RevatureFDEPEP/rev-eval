from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.quiz_session import QuizSession, QuizSessionStatus


class QuizSessionRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: str,
        test_id: int,
        user_id: int,
        session_token: str,
        question_ids: list[str],
        started_at: datetime,
        expires_at: datetime,
    ) -> QuizSession:
        session = QuizSession(
            session_id=session_id,
            test_id=test_id,
            user_id=user_id,
            session_token=session_token,
            question_ids=question_ids,
            current_index=0,
            status=QuizSessionStatus.ACTIVE,
            created_at=started_at,
            started_at=started_at,
            expires_at=expires_at,
        )
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
    async def get_active_by_test_and_user(
        db: AsyncSession, test_id: int, user_id: int
    ) -> QuizSession | None:
        result = await db.execute(
            select(QuizSession)
            .where(
                QuizSession.test_id == test_id,
                QuizSession.user_id == user_id,
                QuizSession.status == QuizSessionStatus.ACTIVE,
            )
            .order_by(QuizSession.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def set_status(
        db: AsyncSession, session: QuizSession, status: QuizSessionStatus
    ) -> QuizSession:
        session.status = status
        if status == QuizSessionStatus.SUBMITTED:
            session.submitted_at = datetime.now(UTC).replace(tzinfo=None)
        elif status == QuizSessionStatus.EXPIRED and session.submitted_at is None:
            # Finalize an expired attempt at its timeout (not at detection time),
            # so any already-scored answers count as a terminal result. EXPIRED
            # stays distinct from SUBMITTED; submitted_at is the "finalized at" time.
            session.submitted_at = session.expires_at
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def save_draft(
        db: AsyncSession,
        session: QuizSession,
        answers: dict[str, list[int]],
        client_version: int,
    ) -> QuizSession:
        """Persist an advisory autosave snapshot and its monotonic version.

        The caller has already row-locked the session and gated on the version
        (only the winning, strictly-fresher snapshot reaches here), so this just
        writes. Does not touch current_index or status."""
        session.draft_answers = answers
        session.draft_version = client_version
        await db.commit()
        return session

    @staticmethod
    async def lock_for_update(db: AsyncSession, session_id: str) -> QuizSession | None:
        """Load a session with SELECT FOR UPDATE (row-level lock on Postgres;
        silently ignored on SQLite used in hermetic tests)."""
        result = await db.execute(
            select(QuizSession)
            .where(QuizSession.session_id == session_id)
            .with_for_update()
        )
        return result.scalars().first()
