# src/repositories/answer_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.answer import QuizAnswer


class AnswerRepository:

    @staticmethod
    async def get_by_session_and_key(
        db: AsyncSession, session_id: str, idempotency_key: str
    ) -> QuizAnswer | None:
        """Return the prior answer recorded under ``idempotency_key`` *within
        this session* (used to replay a retried submission), or None if unseen.

        Scoped to ``session_id`` so a key reused across sessions or users can
        never replay another session's response — the lookup runs only after
        the caller has verified ownership of ``session_id``."""
        result = await db.execute(
            select(QuizAnswer).where(
                QuizAnswer.session_id == session_id,
                QuizAnswer.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().first()

    @staticmethod
    def add(db: AsyncSession, answer: QuizAnswer) -> QuizAnswer:
        """Stage an answer row on the session. The caller owns the surrounding
        transaction (it also mutates the locked session row), so this does NOT
        commit — it only adds to the pending unit of work."""
        db.add(answer)
        return answer
