"""Unit tests for Category Pydantic schemas — pure validation, no DB or async.

W2-F7: mirrors tests/test_skill_schema.py for the new Category domain.
"""

import pytest
from pydantic import ValidationError
from src.schemas.category_schema import (
    CategoryCreate,
    CategoryOut,
    CategorySkillOut,
    CategoryUpdate,
)


def test_category_create_valid():
    c = CategoryCreate(name="Backend", description="FastAPI + SQLAlchemy")
    assert c.name == "Backend"
    assert c.description == "FastAPI + SQLAlchemy"


def test_category_create_description_optional():
    c = CategoryCreate(name="Frontend")
    assert c.description is None


def test_category_create_requires_name():
    with pytest.raises(ValidationError):
        CategoryCreate(description="missing name")


def test_category_update_all_optional():
    u = CategoryUpdate()
    assert u.name is None
    assert u.description is None


def test_category_out_from_attributes():
    class Row:
        id = 11
        name = "DevOps"
        description = None

    out = CategoryOut.model_validate(Row())
    assert out.id == 11
    assert out.name == "DevOps"
    assert out.description is None


def test_category_skill_out_from_attributes():
    class Row:
        id = 3
        category_id = 1
        skill_id = 2

    out = CategorySkillOut.model_validate(Row())
    assert out.id == 3
    assert out.category_id == 1
    assert out.skill_id == 2
