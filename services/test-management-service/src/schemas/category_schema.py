from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategorySkillLink(BaseModel):
    skill_ids: list[int]


class SkillSummary(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryOut(CategoryBase):
    id: int
    skills: list[SkillSummary] = []

    class Config:
        from_attributes = True
