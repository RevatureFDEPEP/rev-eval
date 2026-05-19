from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.skill_service import SkillService
from src.schemas.skill_schema import SkillCreate, SkillUpdate, SkillOut
from src.db.session import get_db

router = APIRouter(prefix="/skills", tags=["Skills"])

@router.post("/", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def create_skill(skill_in: SkillCreate, db: AsyncSession = Depends(get_db)):
    return await SkillService.create_skill(db, skill_in)

@router.get("/", response_model=List[SkillOut])
async def list_skills(db: AsyncSession = Depends(get_db)):
    return await SkillService.list_skills(db)

@router.get("/{skill_id}/", response_model=SkillOut)
async def get_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await SkillService.get_skill_by_id(db, skill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Skill not found")

@router.put("/{skill_id}/", response_model=SkillOut)
async def update_skill(skill_id: int, skill_in: SkillUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await SkillService.update_skill(db, skill_id, skill_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Skill not found")

@router.delete("/{skill_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await SkillService.delete_skill(db, skill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Skill not found")
