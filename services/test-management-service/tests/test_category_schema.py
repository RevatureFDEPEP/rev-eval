"""Schema tests for the Category domain (no DB required)."""
import pytest
from pydantic import ValidationError
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategoryUpdate


def test_category_create_valid():
    c = CategoryCreate(name="Python")
    assert c.name == "Python"
    assert c.description is None


def test_category_create_requires_name():
    with pytest.raises(ValidationError):
        CategoryCreate()


def test_category_update_all_fields_optional():
    c = CategoryUpdate()
    assert c.name is None
    assert c.description is None


def test_category_out_reads_from_orm_attributes_with_nested_skills():
    class SkillRow:
        id = 7
        name = "FastAPI"
        description = None

    class CategoryRow:
        id = 1
        name = "Python"
        description = "Python ecosystem"
        skills = [SkillRow()]

    out = CategoryOut.model_validate(CategoryRow())
    assert out.id == 1
    assert out.name == "Python"
    assert [s.name for s in out.skills] == ["FastAPI"]


def test_category_out_defaults_to_empty_skills():
    class CategoryRow:
        id = 2
        name = "Docker"
        description = None
        skills = []

    assert CategoryOut.model_validate(CategoryRow()).skills == []
