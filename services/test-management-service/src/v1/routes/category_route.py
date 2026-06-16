from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.category_schema import (
    CategoryCreate,
    CategoryOut,
    CategorySkillOut,
    CategoryUpdate,
)
from src.services.category_service import CategoryConflictError, CategoryService
from src.utils.dependencies import get_current_trainer

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_trainer),
):
    try:
        return await CategoryService.create_category(db, category_in)
    except CategoryConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get("/", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.list_categories(db)


@router.get("/{category_id}/", response_model=CategoryOut)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.get_category_by_id(db, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Category not found") from e


@router.put("/{category_id}/", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_trainer),
):
    try:
        return await CategoryService.update_category(db, category_id, category_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Category not found") from e
    except CategoryConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete("/{category_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_trainer),
):
    try:
        await CategoryService.delete_category(db, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Category not found") from e


# ===== CATEGORY-SKILL LINK ENDPOINTS =====
@router.get("/{category_id}/skills/", response_model=list[CategorySkillOut])
async def list_category_skills(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.list_category_skills(db, category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Category not found") from e


@router.post(
    "/{category_id}/skills/{skill_id}/",
    response_model=CategorySkillOut,
    status_code=status.HTTP_201_CREATED,
)
async def link_skill(
    category_id: int,
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_trainer),
):
    try:
        return await CategoryService.link_skill(db, category_id, skill_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except CategoryConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete(
    "/{category_id}/skills/{skill_id}/", status_code=status.HTTP_204_NO_CONTENT
)
async def unlink_skill(
    category_id: int,
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_trainer),
):
    try:
        await CategoryService.unlink_skill(db, category_id, skill_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
