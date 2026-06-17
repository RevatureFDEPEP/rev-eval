from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategoryUpdate
from src.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(category_in: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await CategoryService.create_category(db, category_in)


@router.get("/", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.list_categories(db)


@router.get("/{category_id}/", response_model=CategoryOut)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.get_category_by_id(db, category_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found") from None


@router.put("/{category_id}/", response_model=CategoryOut)
async def update_category(category_id: int, category_in: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await CategoryService.update_category(db, category_id, category_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found") from None


@router.delete("/{category_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await CategoryService.delete_category(db, category_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found") from None


@router.post("/{category_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def link_skill(category_id: int, skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await CategoryService.link_skill(db, category_id, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.delete("/{category_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_skill(category_id: int, skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await CategoryService.unlink_skill(db, category_id, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
