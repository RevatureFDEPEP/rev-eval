from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.skill_repository import SkillRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate, SkillOut

class SkillService:

    @staticmethod
    async def create_skill(db: AsyncSession, skill_in: SkillCreate) -> SkillOut:
        skill = await SkillRepository.create(db, skill_in)
        return SkillOut.from_orm(skill)

    @staticmethod
    async def update_skill(db: AsyncSession, skill_id: int, skill_in: SkillUpdate) -> SkillOut:
        skill = await SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise ValueError("Skill not found")
        skill = await SkillRepository.update(db, skill, skill_in)
        return SkillOut.from_orm(skill)

    @staticmethod
    async def delete_skill(db: AsyncSession, skill_id: int) -> None:
        skill = await SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise ValueError("Skill not found")
        await SkillRepository.delete(db, skill)

    @staticmethod
    async def list_skills(db: AsyncSession) -> List[SkillOut]:
        skills = await SkillRepository.list_all(db)
        return [SkillOut.from_orm(skill) for skill in skills]
