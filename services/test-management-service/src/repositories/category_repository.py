
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.category import Category
from src.schemas.category_schema import CategoryCreate, CategoryUpdate


class CategoryRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Category | None:
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()  # More explicit than .first()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Category]:
        result = await db.execute(select(Category).order_by(Category.id))
        return list(result.scalars().all())  # Ensure it's a list

    @staticmethod
    async def create(db: AsyncSession, category_in: CategoryCreate) -> Category:
        # Use model_dump() for Pydantic v2, dict() for v1
        category_data = category_in.model_dump() if hasattr(category_in, 'model_dump') else category_in.dict()
        category = Category(**category_data)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update(db: AsyncSession, category: Category, category_in: CategoryUpdate) -> Category:
        update_data = category_in.model_dump(exclude_unset=True) if hasattr(category_in, 'model_dump') else category_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        db.add(category)  # Ensure it's tracked
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete(db: AsyncSession, category: Category) -> None:
        await db.delete(category)  # Use await with async session
        await db.commit()
