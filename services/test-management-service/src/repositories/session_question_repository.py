from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session_question import SessionQuestion


class SessionQuestionRepository:

    @staticmethod
    async def bulk_create(db: AsyncSession, session_id: int, question_ids: list[str]) -> list[SessionQuestion]:
        objs = [
            SessionQuestion(session_id=session_id, position=i, question_id=qid)
            for i, qid in enumerate(question_ids)
        ]
        db.add_all(objs)
        await db.flush()
        return objs

    @staticmethod
    async def list_by_session(db: AsyncSession, session_id: int) -> list[SessionQuestion]:
        result = await db.execute(
            select(SessionQuestion)
            .where(SessionQuestion.session_id == session_id)
            .order_by(SessionQuestion.position)
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_position(db: AsyncSession, session_id: int, position: int) -> SessionQuestion | None:
        result = await db.execute(
            select(SessionQuestion)
            .where(SessionQuestion.session_id == session_id, SessionQuestion.position == position)
        )
        return result.scalars().first()
