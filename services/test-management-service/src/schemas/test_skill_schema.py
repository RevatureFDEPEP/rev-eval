from pydantic import BaseModel, ConfigDict


# ===== TEST-SKILL SCHEMAS =====
class TestSkillBase(BaseModel):
    test_id: int
    skill_id: int

class TestSkillCreate(TestSkillBase):
    pass

class TestSkillOut(TestSkillBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
