from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:

    @staticmethod
    async def get(
        db: AsyncSession,
        *,
        idempotency_key: str,
        session_id: str,
    ) -> Optional[IdempotencyKey]:
        result = await db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.session_id == session_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        idempotency_key: str,
        session_id: str,
        response_body: str,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            idempotency_key=idempotency_key,
            session_id=session_id,
            response_body=response_body,
        )
        db.add(record)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            # Race condition: another request stored the key first; return existing
            existing = await IdempotencyRepository.get(
                db, idempotency_key=idempotency_key, session_id=session_id
            )
            return existing  # type: ignore[return-value]
        return record
