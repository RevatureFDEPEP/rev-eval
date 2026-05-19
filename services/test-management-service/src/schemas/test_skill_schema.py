from pydantic import BaseModel

# ===== TEST-SKILL SCHEMAS =====
class TestSkillBase(BaseModel):
    test_id: int
    skill_id: int

class TestSkillCreate(TestSkillBase):
    pass

class TestSkillOut(TestSkillBase):
    id: int

    class Config:
        from_attributes = True
