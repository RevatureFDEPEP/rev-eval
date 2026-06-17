from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.category_repository import CategoryRepository
from src.repositories.skill_repository import SkillRepository
from src.schemas.category_schema import (
    CategoryCreate,
    CategoryOut,
    CategorySkillOut,
    CategoryUpdate,
)


class CategoryConflictError(Exception):
    """Raised when a category operation violates a uniqueness constraint."""


class CategoryService:
    @staticmethod
    async def create_category(
        db: AsyncSession, category_in: CategoryCreate
    ) -> CategoryOut:
        existing = await CategoryRepository.get_by_name(db, category_in.name)
        if existing:
            raise CategoryConflictError(
                f"Category with name '{category_in.name}' already exists"
            )
        try:
            category = await CategoryRepository.create(db, category_in)
        except IntegrityError as e:
            # Defense-in-depth: a concurrent insert can still win the race.
            await db.rollback()
            raise CategoryConflictError(
                f"Category with name '{category_in.name}' already exists"
            ) from e
        return CategoryOut.model_validate(category)

    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        return CategoryOut.model_validate(category)

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[CategoryOut]:
        categories = await CategoryRepository.list_all(db)
        return [CategoryOut.model_validate(c) for c in categories]

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, category_in: CategoryUpdate
    ) -> CategoryOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        if category_in.name is not None and category_in.name != category.name:
            existing = await CategoryRepository.get_by_name(db, category_in.name)
            if existing:
                raise CategoryConflictError(
                    f"Category with name '{category_in.name}' already exists"
                )
        try:
            category = await CategoryRepository.update(db, category, category_in)
        except IntegrityError as e:
            await db.rollback()
            raise CategoryConflictError(
                f"Category with name '{category_in.name}' already exists"
            ) from e
        return CategoryOut.model_validate(category)

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int) -> None:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        await CategoryRepository.delete(db, category)

    # ===== CATEGORY-SKILL LINK OPERATIONS =====
    @staticmethod
    async def list_category_skills(
        db: AsyncSession, category_id: int
    ) -> list[CategorySkillOut]:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        links = await CategoryRepository.list_links(db, category_id)
        return [CategorySkillOut.model_validate(link) for link in links]

    @staticmethod
    async def link_skill(
        db: AsyncSession, category_id: int, skill_id: int
    ) -> CategorySkillOut:
        category = await CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        skill = await SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise ValueError("Skill not found")
        existing = await CategoryRepository.get_link(db, category_id, skill_id)
        if existing:
            raise CategoryConflictError("Skill is already linked to this category")
        try:
            link = await CategoryRepository.create_link(db, category_id, skill_id)
        except IntegrityError as e:
            await db.rollback()
            raise CategoryConflictError(
                "Skill is already linked to this category"
            ) from e
        return CategorySkillOut.model_validate(link)

    @staticmethod
    async def unlink_skill(db: AsyncSession, category_id: int, skill_id: int) -> None:
        link = await CategoryRepository.get_link(db, category_id, skill_id)
        if not link:
            raise ValueError("Skill is not linked to this category")
        await CategoryRepository.delete_link(db, link)
