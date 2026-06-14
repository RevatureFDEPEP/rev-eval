from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.category_repository import CategoryRepository
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategorySkillLink, CategoryUpdate


class CategoryService:
    @staticmethod
    async def create_category(db: AsyncSession, category_in: CategoryCreate) -> CategoryOut:
        existing = await CategoryRepository.get_by_name(db, category_in.name)
        if existing:
            raise ValueError(f"Category '{category_in.name}' already exists")
        category = await CategoryRepository.create(db, category_in)
        category = await CategoryRepository.get_by_id(db, category.id)
        return CategoryOut.from_orm(category)

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[CategoryOut]:
        categories = await CategoryRepository.list_all(db)
        return [CategoryOut.from_orm(c) for c in categories]

    @staticmethod
    async def get_category(db: AsyncSession, category_id: int) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        return CategoryOut.from_orm(category)

    @staticmethod
    async def update_category(db: AsyncSession, category_id: int, category_in: CategoryUpdate) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        if category_in.name and category_in.name != category.name:
            existing = await CategoryRepository.get_by_name(db, category_in.name)
            if existing:
                raise ValueError(f"Category '{category_in.name}' already exists")
        category = await CategoryRepository.update(db, category, category_in)
        category = await CategoryRepository.get_by_id(db, category.id)
        return CategoryOut.from_orm(category)

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int) -> None:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        await CategoryRepository.delete(db, category)

    @staticmethod
    async def link_skills(db: AsyncSession, category_id: int, link: CategorySkillLink) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        skills = await CategoryRepository.get_skills_by_ids(db, link.skill_ids)
        found_ids = {s.id for s in skills}
        missing = set(link.skill_ids) - found_ids
        if missing:
            raise ValueError(f"Skills not found: {sorted(missing)}")
        category = await CategoryRepository.set_skills(db, category, skills)
        category = await CategoryRepository.get_by_id(db, category.id)
        return CategoryOut.from_orm(category)
