from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.category import Category
from src.schemas.category_schema import CategoryCreate, CategoryUpdate


class CategoryRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> List[Category]:
        result = await db.execute(select(Category).order_by(Category.id))
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, category_in: CategoryCreate) -> Category:
        category = Category(**category_in.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update(db: AsyncSession, category: Category, category_in: CategoryUpdate) -> Category:
        for field, value in category_in.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete(db: AsyncSession, category: Category) -> None:
        await db.delete(category)
        await db.commit()
