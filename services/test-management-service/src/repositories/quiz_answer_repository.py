from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.quiz_answer import QuizAnswer


class QuizAnswerRepository:

    @staticmethod
    async def add(db: AsyncSession, answer: QuizAnswer) -> QuizAnswer:
        db.add(answer)
        await db.flush()
        return answer

    @staticmethod
    async def get_by_session_and_index(
        db: AsyncSession, quiz_session_id: int, question_index: int
    ) -> Optional[QuizAnswer]:
        result = await db.execute(
            select(QuizAnswer).where(
                QuizAnswer.quiz_session_id == quiz_session_id,
                QuizAnswer.question_index == question_index,
            )
        )
        return result.scalars().first()
