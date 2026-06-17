import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:
    @staticmethod
    async def get_by_key(db: AsyncSession, key: str) -> IdempotencyKey | None:
        result = await db.execute(select(IdempotencyKey).where(IdempotencyKey.key == key))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        key: str,
        session_id: uuid.UUID,
        response_json: dict,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            key=key,
            session_id=session_id,
            response_json=response_json,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        return record
