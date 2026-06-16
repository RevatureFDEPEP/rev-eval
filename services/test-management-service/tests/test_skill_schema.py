"""Unit tests for Skill Pydantic schemas — pure validation, no DB or async.

First tests under the W2-F2 pytest scaffold for test-management-service.
"""

import pytest
from pydantic import ValidationError

from src.schemas.skill_schema import SkillCreate, SkillOut, SkillUpdate


def test_skill_create_valid():
    s = SkillCreate(name="Python", description="async + FastAPI")
    assert s.name == "Python"
    assert s.description == "async + FastAPI"


def test_skill_create_description_optional():
    s = SkillCreate(name="Docker")
    assert s.description is None


def test_skill_create_requires_name():
    with pytest.raises(ValidationError):
        SkillCreate(description="missing name")


def test_skill_update_all_optional():
    u = SkillUpdate()
    assert u.name is None
    assert u.description is None


def test_skill_out_from_attributes():
    class Row:
        id = 7
        name = "SQL"
        description = None

    out = SkillOut.model_validate(Row())
    assert out.id == 7
    assert out.name == "SQL"
