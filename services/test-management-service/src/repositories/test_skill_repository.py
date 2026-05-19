from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.test_skill import TestSkill
from src.schemas.test_skill_schema import TestSkillCreate

class TestSkillRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, ts_id: int) -> Optional[TestSkill]:
        result = await db.execute(select(TestSkill).where(TestSkill.id == ts_id))
        return result.scalars().first()

    @staticmethod
    async def list_by_test(db: AsyncSession, test_id: int) -> List[TestSkill]:
        result = await db.execute(select(TestSkill).where(TestSkill.test_id == test_id))
        return result.scalars().all()

    @staticmethod
    async def list_by_skill(db: AsyncSession, skill_id: int) -> List[TestSkill]:
        result = await db.execute(select(TestSkill).where(TestSkill.skill_id == skill_id))
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, ts_in: TestSkillCreate) -> TestSkill:
        ts = TestSkill(**ts_in.dict())  # ts_in is always a Pydantic model
        db.add(ts)
        await db.commit()
        await db.refresh(ts)
        return ts

    @staticmethod
    async def delete(db: AsyncSession, ts: TestSkill) -> None:
        await db.delete(ts)
        await db.commit()
