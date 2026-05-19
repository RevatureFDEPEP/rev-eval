from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from src.models.test import TestType
from src.schemas.skill_schema import SkillOut

# ===== TEST SCHEMAS =====
class TestBase(BaseModel):
    name: str
    test_type: TestType
    role: Optional[str] = None
    curriculum: Optional[str] = None
    duration_seconds: Optional[int] = None  # convert Interval to seconds
    number_of_questions: Optional[int] = 20  # Total number of questions
    active: Optional[bool] = True

class TestCreate(TestBase):
    skill_ids: Optional[List[int]] = []  # Skills linked to test
    created_by_id: Optional[int] = None  # User Service ID

class TestUpdate(BaseModel):
    name: Optional[str] = None
    test_type: Optional[TestType] = None
    role: Optional[str] = None
    curriculum: Optional[str] = None
    duration_seconds: Optional[int] = None
    number_of_questions: Optional[int] = None
    active: Optional[bool] = None
    skill_ids: Optional[List[int]] = None

class TestOut(TestBase):
    id: int
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None  # Fetched from User Service
    created_at: datetime
    updated_at: datetime
    skills: List[SkillOut] = []

    class Config:
        from_attributes = True
