from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas.category_schema import CategoryCreate, CategoryOut, CategoryUpdate


class TestCategoryCreate:
    def test_valid_minimal(self):
        cat = CategoryCreate(name="Backend")
        assert cat.name == "Backend"
        assert cat.description is None

    def test_valid_with_description(self):
        cat = CategoryCreate(name="Backend", description="Server-side topics")
        assert cat.description == "Server-side topics"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            CategoryCreate()

    def test_name_must_be_present_when_only_description(self):
        with pytest.raises(ValidationError):
            CategoryCreate(description="no name")


class TestCategoryUpdate:
    def test_all_optional(self):
        upd = CategoryUpdate()
        assert upd.name is None
        assert upd.description is None

    def test_partial_name_only(self):
        upd = CategoryUpdate(name="Frontend")
        assert upd.name == "Frontend"
        assert upd.description is None

    def test_partial_description_only(self):
        upd = CategoryUpdate(description="UI topics")
        assert upd.description == "UI topics"
        assert upd.name is None


class TestCategoryOut:
    def test_from_attributes(self):
        now = datetime(2026, 6, 11, 12, 0, 0)

        class _Row:
            id = 7
            name = "Backend"
            description = "Server-side topics"
            created_at = now
            updated_at = now

        out = CategoryOut.model_validate(_Row())
        assert out.id == 7
        assert out.name == "Backend"
        assert out.created_at == now
        assert out.updated_at == now
