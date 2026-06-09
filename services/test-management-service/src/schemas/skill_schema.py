from typing import Optional

from pydantic import BaseModel, ConfigDict


# ===== SKILL SCHEMAS =====
class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SkillOut(SkillBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
