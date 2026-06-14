from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategorySkillLink, CategoryUpdate
from src.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(category_in: CategoryCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.create_category(db, category_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.list_categories(db)


@router.get("/{category_id}/", response_model=CategoryOut)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.get_category(db, category_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from None


@router.put("/{category_id}/", response_model=CategoryOut)
async def update_category(category_id: int, category_in: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.update_category(db, category_id, category_in)
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_409_CONFLICT if "already exists" in detail else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=detail) from None


@router.delete("/{category_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await CategoryService.delete_category(db, category_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from None


@router.post("/{category_id}/skills", response_model=CategoryOut)
async def link_skills(category_id: int, link: CategorySkillLink, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.link_skills(db, category_id, link)
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=detail) from None
