from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sql_delete
from src.models.skill import Skill
from src.schemas.skill_schema import SkillCreate, SkillUpdate

class SkillRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, skill_id: int) -> Optional[Skill]:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        return result.scalar_one_or_none()  # More explicit than .first()
    
    @staticmethod
    async def list_all(db: AsyncSession) -> List[Skill]:
        result = await db.execute(select(Skill).order_by(Skill.id))
        return list(result.scalars().all())  # Ensure it's a list
    
    @staticmethod
    async def create(db: AsyncSession, skill_in: SkillCreate) -> Skill:
        # Use model_dump() for Pydantic v2, dict() for v1
        skill_data = skill_in.model_dump() if hasattr(skill_in, 'model_dump') else skill_in.dict()
        skill = Skill(**skill_data)
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return skill
    
    @staticmethod
    async def update(db: AsyncSession, skill: Skill, skill_in: SkillUpdate) -> Skill:
        update_data = skill_in.model_dump(exclude_unset=True) if hasattr(skill_in, 'model_dump') else skill_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)
        db.add(skill)  # Ensure it's tracked
        await db.commit()
        await db.refresh(skill)
        return skill
    
    @staticmethod
    async def delete(db: AsyncSession, skill: Skill) -> None:
        await db.delete(skill)  # Use await with async session
        await db.commit()