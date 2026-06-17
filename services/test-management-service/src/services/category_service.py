from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.category_repository import CategoryRepository
from src.repositories.skill_repository import SkillRepository
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategoryUpdate


class CategoryService:
    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        return CategoryOut.model_validate(category)

    @staticmethod
    async def list_categories(db: AsyncSession) -> List[CategoryOut]:
        categories = await CategoryRepository.list_all(db)
        return [CategoryOut.model_validate(c) for c in categories]

    @staticmethod
    async def create_category(db: AsyncSession, category_in: CategoryCreate) -> CategoryOut:
        category = await CategoryRepository.create(db, category_in)
        return CategoryOut.model_validate(category)

    @staticmethod
    async def update_category(db: AsyncSession, category_id: int, category_in: CategoryUpdate) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        category = await CategoryRepository.update(db, category, category_in)
        return CategoryOut.model_validate(category)

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int) -> None:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        await CategoryRepository.delete(db, category)

    @staticmethod
    async def link_skill(db: AsyncSession, category_id: int, skill_id: int) -> None:
        category = await CategoryRepository.get_by_id_with_skills(db, category_id)
        if not category:
            raise ValueError("Category not found")
        skill = await SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise ValueError("Skill not found")
        if skill in category.skills:
            return
        await CategoryRepository.link_skill(db, category, skill)

    @staticmethod
    async def unlink_skill(db: AsyncSession, category_id: int, skill_id: int) -> None:
        category = await CategoryRepository.get_by_id_with_skills(db, category_id)
        if not category:
            raise ValueError("Category not found")
        skill = await SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise ValueError("Skill not found")
        if skill not in category.skills:
            raise ValueError("Skill not linked to this category")
        await CategoryRepository.unlink_skill(db, category, skill)
