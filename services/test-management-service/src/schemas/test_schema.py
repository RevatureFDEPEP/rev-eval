from datetime import datetime

from pydantic import BaseModel
from src.models.test import TestType
from src.schemas.skill_schema import SkillOut


# ===== TEST SCHEMAS =====
class TestBase(BaseModel):
    name: str
    test_type: TestType
    role: str | None = None
    curriculum: str | None = None
    duration_seconds: int | None = None  # convert Interval to seconds
    number_of_questions: int | None = 20  # Total number of questions
    active: bool | None = True

class TestCreate(TestBase):
    skill_ids: list[int] | None = []  # Skills linked to test
    created_by_id: int | None = None  # User Service ID

class TestUpdate(BaseModel):
    name: str | None = None
    test_type: TestType | None = None
    role: str | None = None
    curriculum: str | None = None
    duration_seconds: int | None = None
    number_of_questions: int | None = None
    active: bool | None = None
    skill_ids: list[int] | None = None

class TestOut(TestBase):
    id: int
    created_by_id: int | None = None
    created_by_name: str | None = None  # Fetched from User Service
    created_at: datetime
    updated_at: datetime
    skills: list[SkillOut] = []

    class Config:
        from_attributes = True
