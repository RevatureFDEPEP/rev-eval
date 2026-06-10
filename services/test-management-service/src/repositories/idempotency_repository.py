from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:

    @staticmethod
    async def get(
        db: AsyncSession, session_id: UUID, idempotency_key: str
    ) -> Optional[IdempotencyKey]:
        result = await db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.session_id == session_id,
                IdempotencyKey.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, record: IdempotencyKey) -> IdempotencyKey:
        """Stage a dedup record (committed with the rest of the transaction)."""
        db.add(record)
        await db.flush()
        return record
