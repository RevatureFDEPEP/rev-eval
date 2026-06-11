# src/repositories/answer_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.answer import QuizAnswer


class AnswerRepository:

    @staticmethod
    async def get_by_idempotency_key(
        db: AsyncSession, idempotency_key: str
    ) -> QuizAnswer | None:
        """Return the prior answer recorded under ``idempotency_key`` (used to
        replay a retried submission), or None if the key is unseen."""
        result = await db.execute(
            select(QuizAnswer).where(QuizAnswer.idempotency_key == idempotency_key)
        )
        return result.scalars().first()

    @staticmethod
    def add(db: AsyncSession, answer: QuizAnswer) -> QuizAnswer:
        """Stage an answer row on the session. The caller owns the surrounding
        transaction (it also mutates the locked session row), so this does NOT
        commit — it only adds to the pending unit of work."""
        db.add(answer)
        return answer
