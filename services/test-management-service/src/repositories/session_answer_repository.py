import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session_answer import SessionAnswer


class SessionAnswerRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        session_id: uuid.UUID,
        question_id: str,
        question_index: int,
        submitted_answers: list[str],
        earned_points: float,
        max_points: float,
        is_correct: bool,
    ) -> SessionAnswer:
        answer = SessionAnswer(
            session_id=session_id,
            question_id=question_id,
            question_index=question_index,
            submitted_answers=submitted_answers,
            earned_points=earned_points,
            max_points=max_points,
            is_correct=is_correct,
            answered_at=datetime.utcnow(),
        )
        db.add(answer)
        return answer

    @staticmethod
    async def list_by_session(db: AsyncSession, session_id: uuid.UUID) -> list[SessionAnswer]:
        result = await db.execute(
            select(SessionAnswer)
            .where(SessionAnswer.session_id == session_id)
            .order_by(SessionAnswer.question_index)
        )
        return list(result.scalars().all())
