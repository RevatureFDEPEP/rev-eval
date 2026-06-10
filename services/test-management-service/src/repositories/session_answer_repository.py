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
    async def create(
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
        await db.commit()
        await db.refresh(answer)
        return answer
