from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models.category import Category
from src.models.skill import Skill
from src.schemas.category_schema import CategoryCreate, CategoryUpdate


class CategoryRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Category | None:
        result = await db.execute(
            select(Category)
            .options(selectinload(Category.skills))
            .where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Category | None:
        result = await db.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Category]:
        result = await db.execute(
            select(Category).options(selectinload(Category.skills)).order_by(Category.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, category_in: CategoryCreate) -> Category:
        data = category_in.model_dump() if hasattr(category_in, "model_dump") else category_in.dict()
        category = Category(**data)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update(db: AsyncSession, category: Category, category_in: CategoryUpdate) -> Category:
        update_data = (
            category_in.model_dump(exclude_unset=True)
            if hasattr(category_in, "model_dump")
            else category_in.dict(exclude_unset=True)
        )
        for field, value in update_data.items():
            setattr(category, field, value)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete(db: AsyncSession, category: Category) -> None:
        await db.delete(category)
        await db.commit()

    @staticmethod
    async def set_skills(db: AsyncSession, category: Category, skills: list[Skill]) -> Category:
        category.skills = skills
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def get_skills_by_ids(db: AsyncSession, skill_ids: list[int]) -> list[Skill]:
        result = await db.execute(select(Skill).where(Skill.id.in_(skill_ids)))
        return list(result.scalars().all())
