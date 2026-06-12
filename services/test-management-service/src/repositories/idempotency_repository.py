from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:

    @staticmethod
    async def get(
        db: AsyncSession, quiz_session_id: int, key: str
    ) -> Optional[IdempotencyKey]:
        result = await db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.quiz_session_id == quiz_session_id,
                IdempotencyKey.key == key,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def add(db: AsyncSession, record: IdempotencyKey) -> IdempotencyKey:
        db.add(record)
        await db.flush()
        return record
