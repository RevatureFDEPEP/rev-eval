from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.quiz_session import (
    IdempotencyRecord,
    QuizAnswer,
    QuizSession,
    QuizSessionQuestion,
    SessionStatus,
)


class QuizSessionRepository:

    @staticmethod
    async def create(db: AsyncSession, session: QuizSession) -> QuizSession:
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def count_active_for_user(db: AsyncSession, user_id: int) -> int:
        """Count in-progress sessions for a user (anti-abuse guard)."""
        result = await db.execute(
            select(func.count())
            .select_from(QuizSession)
            .where(
                QuizSession.user_id == user_id,
                QuizSession.status == SessionStatus.in_progress,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def add_question(db: AsyncSession, question: QuizSessionQuestion) -> None:
        db.add(question)

    @staticmethod
    async def get_by_session_id(
        db: AsyncSession, session_id: str
    ) -> Optional[QuizSession]:
        result = await db.execute(
            select(QuizSession).where(QuizSession.session_id == session_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_session_id_for_update(
        db: AsyncSession, session_id: str
    ) -> Optional[QuizSession]:
        """Fetch a session with a row-level write lock.

        ``with_for_update`` serializes concurrent answer/submit requests against
        the same session on Postgres (it is a harmless no-op on SQLite used in
        tests), preventing lost updates to attempt state.
        """
        result = await db.execute(
            select(QuizSession)
            .where(QuizSession.session_id == session_id)
            .with_for_update()
        )
        return result.scalars().first()

    @staticmethod
    async def get_questions_for_session(
        db: AsyncSession, quiz_session_id: int
    ) -> List[QuizSessionQuestion]:
        result = await db.execute(
            select(QuizSessionQuestion)
            .where(QuizSessionQuestion.quiz_session_id == quiz_session_id)
            .order_by(QuizSessionQuestion.question_index)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_answers_for_session(
        db: AsyncSession, quiz_session_id: int
    ) -> List[QuizAnswer]:
        result = await db.execute(
            select(QuizAnswer).where(QuizAnswer.quiz_session_id == quiz_session_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_answer(
        db: AsyncSession, quiz_session_id: int, question_index: int
    ) -> Optional[QuizAnswer]:
        result = await db.execute(
            select(QuizAnswer).where(
                QuizAnswer.quiz_session_id == quiz_session_id,
                QuizAnswer.question_index == question_index,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def add_answer(db: AsyncSession, answer: QuizAnswer) -> None:
        db.add(answer)

    @staticmethod
    async def get_idempotency_record(
        db: AsyncSession, quiz_session_id: int, idempotency_key: str
    ) -> Optional[IdempotencyRecord]:
        result = await db.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.quiz_session_id == quiz_session_id,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def add_idempotency_record(
        db: AsyncSession, record: IdempotencyRecord
    ) -> None:
        db.add(record)
