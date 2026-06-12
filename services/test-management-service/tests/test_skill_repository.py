import pytest
from src.repositories.skill_repository import SkillRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate


@pytest.mark.parametrize(
    "name,description",
    [
        ("Python Basics", "Foundational Python programming concepts"),
        ("SQL Queries", "Database querying with SELECT, JOIN, and aggregates"),
        ("Java OOP", None),
    ],
)
async def test_skill_create_persists_and_get_by_id_returns_match(name, description, db):
    created = await SkillRepository.create(db, SkillCreate(name=name, description=description))
    assert created.id is not None

    fetched = await SkillRepository.get_by_id(db, created.id)
    assert fetched is not None
    assert fetched.name == name
    assert fetched.description == description


async def test_skill_update_modifies_name_and_leaves_description_unchanged(db):
    original = await SkillRepository.create(db, SkillCreate(name="Legacy Name", description="Keep this description"))
    updated = await SkillRepository.update(db, original, SkillUpdate(name="Updated Name"))
    assert updated.name == "Updated Name"
    assert updated.description == "Keep this description"
