from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from src.schemas.skill_schema import SkillOut


# ===== CATEGORY SCHEMAS =====
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryOut(CategoryBase):
    id: int
    skills: List[SkillOut] = []

    model_config = ConfigDict(from_attributes=True)
