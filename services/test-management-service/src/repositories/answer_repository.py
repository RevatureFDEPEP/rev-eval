from sqlalchemy.ext.asyncio import AsyncSession
from src.models.answer import Answer


class AnswerRepository:

    @staticmethod
    async def create(db: AsyncSession, answer: Answer) -> Answer:
        """Stage a scored answer row. The answer endpoint owns the transaction
        and commits once at the end, so this flushes rather than commits."""
        db.add(answer)
        await db.flush()
        return answer
