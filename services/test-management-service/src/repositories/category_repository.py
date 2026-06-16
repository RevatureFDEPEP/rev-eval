from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.category import Category, CategorySkill
from src.schemas.category_schema import CategoryCreate, CategoryUpdate


class CategoryRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Category | None:
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Category | None:
        result = await db.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Category]:
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
    async def update(
        db: AsyncSession, category: Category, category_in: CategoryUpdate
    ) -> Category:
        update_data = category_in.model_dump(exclude_unset=True)
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

    # ===== CATEGORY-SKILL LINK OPERATIONS =====
    @staticmethod
    async def get_link(
        db: AsyncSession, category_id: int, skill_id: int
    ) -> CategorySkill | None:
        result = await db.execute(
            select(CategorySkill).where(
                CategorySkill.category_id == category_id,
                CategorySkill.skill_id == skill_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_links(db: AsyncSession, category_id: int) -> list[CategorySkill]:
        result = await db.execute(
            select(CategorySkill).where(CategorySkill.category_id == category_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_link(
        db: AsyncSession, category_id: int, skill_id: int
    ) -> CategorySkill:
        link = CategorySkill(category_id=category_id, skill_id=skill_id)
        db.add(link)
        await db.commit()
        await db.refresh(link)
        return link

    @staticmethod
    async def delete_link(db: AsyncSession, link: CategorySkill) -> None:
        await db.delete(link)
        await db.commit()
