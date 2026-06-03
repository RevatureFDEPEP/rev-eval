"""Smoke / sanity tests for test-management-service.

No DB required. These cover the skill Pydantic schemas (create/update/out)
and the settings-derived SQLAlchemy URL.
"""
import pytest
from pydantic import ValidationError
from src.config.settings import settings
from src.schemas.skill_schema import SkillCreate, SkillOut, SkillUpdate


def test_skill_create_valid():
    s = SkillCreate(name="Python")
    assert s.name == "Python"
    assert s.description is None


def test_skill_create_requires_name():
    with pytest.raises(ValidationError):
        SkillCreate()


def test_skill_update_all_fields_optional():
    s = SkillUpdate()
    assert s.name is None
    assert s.description is None


def test_skill_out_reads_from_orm_attributes():
    class Row:
        id = 3
        name = "SQL"
        description = "databases"

    out = SkillOut.model_validate(Row())
    assert out.id == 3
    assert out.name == "SQL"
    assert out.description == "databases"


def test_database_url_format():
    url = settings.SQLALCHEMY_DATABASE_URL
    assert url.startswith("postgresql+psycopg2://")
    assert settings.DB_NAME in url
