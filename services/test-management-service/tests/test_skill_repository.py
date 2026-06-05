import pytest
from src.repositories.skill_repository import SkillRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate


class TestSkillRepository:
    async def test_create_skill(self, db):
        skill = await SkillRepository.create(db, SkillCreate(name="Python", description="Python lang"))
        assert skill.id is not None
        assert skill.name == "Python"
        assert skill.description == "Python lang"

    async def test_get_by_id_found(self, db):
        created = await SkillRepository.create(db, SkillCreate(name="Java"))
        found = await SkillRepository.get_by_id(db, created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_id_not_found_returns_none(self, db):
        result = await SkillRepository.get_by_id(db, 99999)
        assert result is None

    async def test_list_all_empty_returns_empty_list(self, db):
        skills = await SkillRepository.list_all(db)
        assert skills == []

    async def test_list_all_returns_all_skills(self, db):
        await SkillRepository.create(db, SkillCreate(name="Python"))
        await SkillRepository.create(db, SkillCreate(name="Java"))
        await SkillRepository.create(db, SkillCreate(name="SQL"))
        skills = await SkillRepository.list_all(db)
        assert len(skills) == 3

    async def test_list_all_ordered_by_id(self, db):
        s1 = await SkillRepository.create(db, SkillCreate(name="Alpha"))
        s2 = await SkillRepository.create(db, SkillCreate(name="Beta"))
        skills = await SkillRepository.list_all(db)
        assert skills[0].id == s1.id
        assert skills[1].id == s2.id

    async def test_update_name(self, db):
        skill = await SkillRepository.create(db, SkillCreate(name="Old Name"))
        updated = await SkillRepository.update(db, skill, SkillUpdate(name="New Name"))
        assert updated.name == "New Name"

    async def test_update_description(self, db):
        skill = await SkillRepository.create(db, SkillCreate(name="Skill", description="Old desc"))
        updated = await SkillRepository.update(db, skill, SkillUpdate(description="New desc"))
        assert updated.description == "New desc"

    async def test_update_preserves_unchanged_fields(self, db):
        skill = await SkillRepository.create(db, SkillCreate(name="Preserve", description="Keep me"))
        updated = await SkillRepository.update(db, skill, SkillUpdate(name="Changed"))
        assert updated.description == "Keep me"

    async def test_delete_removes_skill(self, db):
        skill = await SkillRepository.create(db, SkillCreate(name="To Delete"))
        skill_id = skill.id
        await SkillRepository.delete(db, skill)
        assert await SkillRepository.get_by_id(db, skill_id) is None

    async def test_delete_does_not_affect_others(self, db):
        s1 = await SkillRepository.create(db, SkillCreate(name="Keep"))
        s2 = await SkillRepository.create(db, SkillCreate(name="Delete"))
        await SkillRepository.delete(db, s2)
        assert await SkillRepository.get_by_id(db, s1.id) is not None

    @pytest.mark.parametrize("name,description", [
        ("Python", "Python programming"),
        ("Java", None),
        ("SQL", "Structured Query Language"),
        ("React", "JavaScript UI library"),
    ])
    async def test_create_various_skills(self, db, name, description):
        skill = await SkillRepository.create(db, SkillCreate(name=name, description=description))
        assert skill.name == name
        assert skill.description == description
