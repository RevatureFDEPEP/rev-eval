import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.schemas.skill_schema import SkillCreate, SkillOut, SkillUpdate


def test_skill_create_valid():
    skill = SkillCreate(name="Docker")
    assert skill.name == "Docker"


def test_skill_create_name_required():
    with pytest.raises(ValidationError):
        SkillCreate()


def test_skill_create_optional_description():
    skill = SkillCreate(name="Python", description="Python programming")
    assert skill.description == "Python programming"


def test_skill_out_serializes_id():
    skill = SkillOut(id=7, name="Kubernetes")
    assert skill.id == 7
    assert skill.name == "Kubernetes"


def test_skill_update_all_optional():
    update = SkillUpdate()
    assert update.name is None
    assert update.description is None


def test_skill_update_partial():
    update = SkillUpdate(name="Updated")
    assert update.name == "Updated"
    assert update.description is None


def test_sqlalchemy_url_contains_host():
    s = Settings(
        DB_HOST="testhost",
        DB_PORT=5432,
        DB_USERNAME="testuser",
        DB_PASSWORD="testpass",
        DB_NAME="testdb",
        ALLOW_ORIGINS="*",
        SERVICE_NAME="test-management-service",
        PORT=8001,
        SERVICE_HOSTNAME="localhost",
    )
    url = s.SQLALCHEMY_DATABASE_URL
    assert "testhost" in url
    assert "testdb" in url
    assert "testuser" in url


def test_sqlalchemy_url_uses_psycopg2_driver():
    s = Settings(
        DB_HOST="db",
        DB_PORT=5432,
        DB_USERNAME="u",
        DB_PASSWORD="p",
        DB_NAME="mydb",
        ALLOW_ORIGINS="*",
        SERVICE_NAME="test-management-service",
        PORT=8001,
        SERVICE_HOSTNAME="localhost",
    )
    assert "psycopg2" in s.SQLALCHEMY_DATABASE_URL
