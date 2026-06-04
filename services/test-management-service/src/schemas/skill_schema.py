
from pydantic import BaseModel


# ===== SKILL SCHEMAS =====
class SkillBase(BaseModel):
    name: str
    description: str | None = None

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class SkillOut(SkillBase):
    id: int

    class Config:
        from_attributes = True
