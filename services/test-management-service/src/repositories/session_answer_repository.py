from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.session_answer import SessionAnswer


class SessionAnswerRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: str,
        question_id: str,
        submitted_answers: list,
        score: float,
        is_correct: bool,
    ) -> SessionAnswer:
        answer = SessionAnswer(
            session_id=session_id,
            question_id=question_id,
            submitted_answers=submitted_answers,
            score=score,
            is_correct=is_correct,
        )
        db.add(answer)
        await db.flush()  # caller commits as part of the surrounding transaction
        return answer

    @staticmethod
    async def list_by_session(db: AsyncSession, session_id: str) -> List[SessionAnswer]:
        result = await db.execute(
            select(SessionAnswer).where(SessionAnswer.session_id == session_id)
        )
        return list(result.scalars().all())
