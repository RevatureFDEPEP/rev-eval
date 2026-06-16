from pydantic import BaseModel


# ===== CATEGORY SCHEMAS =====
class CategoryBase(BaseModel):
    name: str
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# ===== CATEGORY-SKILL LINK SCHEMAS =====
class CategorySkillOut(BaseModel):
    id: int
    category_id: int
    skill_id: int

    class Config:
        from_attributes = True
