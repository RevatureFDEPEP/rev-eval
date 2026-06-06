from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.models.category import Category
from src.models.skill import Skill
from src.schemas.category_schema import CategoryCreate, CategoryUpdate

# Note: Category.skills is always eager-loaded (selectinload) — lazy loading
# after the session's greenlet context raises MissingGreenlet under asyncpg.


class CategoryRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
        result = await db.execute(
            select(Category)
            .options(selectinload(Category.skills))
            .where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> List[Category]:
        result = await db.execute(
            select(Category).options(selectinload(Category.skills)).order_by(Category.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, category_in: CategoryCreate) -> Category:
        category = Category(**category_in.model_dump())
        db.add(category)
        await db.commit()
        # Re-fetch with skills eager-loaded (a plain refresh would leave the
        # relationship unloaded and trip async lazy-loading on serialization).
        return await CategoryRepository.get_by_id(db, category.id)

    @staticmethod
    async def update(
        db: AsyncSession, category: Category, category_in: CategoryUpdate
    ) -> Category:
        update_data = category_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        db.add(category)
        await db.commit()
        return await CategoryRepository.get_by_id(db, category.id)

    @staticmethod
    async def delete(db: AsyncSession, category: Category) -> None:
        await db.delete(category)
        await db.commit()

    @staticmethod
    async def link_skill(db: AsyncSession, category: Category, skill: Skill) -> Category:
        """Attach a skill to a category. Idempotent on duplicate links."""
        if all(s.id != skill.id for s in category.skills):
            category.skills.append(skill)
            await db.commit()
        return await CategoryRepository.get_by_id(db, category.id)

    @staticmethod
    async def unlink_skill(db: AsyncSession, category: Category, skill: Skill) -> Category:
        """Detach a skill from a category. Idempotent on missing links."""
        for linked in list(category.skills):
            if linked.id == skill.id:
                category.skills.remove(linked)
                await db.commit()
                break
        return await CategoryRepository.get_by_id(db, category.id)
