from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.session_answer import SessionAnswer


class SessionAnswerRepository:
    @staticmethod
    async def find_by_idempotency_key(
        db: AsyncSession, session_id: str, idempotency_key: str
    ) -> SessionAnswer | None:
        result = await db.execute(
            select(SessionAnswer).where(
                SessionAnswer.session_id == session_id,
                SessionAnswer.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().first()

    @staticmethod
    def add(
        db: AsyncSession,
        *,
        session_id: str,
        question_id: str,
        question_index: int,
        submitted_answers: list[Any],
        is_correct: bool,
        points_earned: float,
        max_points: float = 1.0,
        requires_manual_review: bool = False,
        idempotency_key: str | None = None,
    ) -> SessionAnswer:
        """Stage a scored answer on the session WITHOUT committing.

        The caller commits once so the answer insert and the session index
        advance land in a single transaction (and a single FOR UPDATE window).
        """
        answer = SessionAnswer(
            session_id=session_id,
            question_id=question_id,
            question_index=question_index,
            submitted_answers=submitted_answers,
            is_correct=is_correct,
            points_earned=points_earned,
            max_points=max_points,
            requires_manual_review=requires_manual_review,
            idempotency_key=idempotency_key,
        )
        db.add(answer)
        return answer
