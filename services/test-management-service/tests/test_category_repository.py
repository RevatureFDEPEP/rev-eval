"""Repository-level tests for CategoryRepository against a hermetic DB.

These run real SQLAlchemy CRUD against the in-memory SQLite `db_session`
fixture (conftest.py) — no Postgres, no Alembic. They cover the documented
repo edge cases: skills are always eager-loaded, and link/unlink are
idempotent.
"""
import pytest
from src.models.skill import Skill
from src.repositories.category_repository import CategoryRepository
from src.schemas.category_schema import CategoryCreate, CategoryUpdate


async def _make_skill(db_session, name="FastAPI") -> Skill:
    skill = Skill(name=name)
    db_session.add(skill)
    await db_session.commit()
    await db_session.refresh(skill)
    return skill


async def test_create_then_get_by_id(db_session):
    created = await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    assert created.id is not None
    assert created.name == "Python"
    # skills is eager-loaded — accessing it must not trip async lazy-loading.
    assert created.skills == []

    fetched = await CategoryRepository.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.name == "Python"


async def test_get_by_id_missing_returns_none(db_session):
    assert await CategoryRepository.get_by_id(db_session, 9999) is None


async def test_list_all_ordered_by_id(db_session):
    await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    await CategoryRepository.create(db_session, CategoryCreate(name="Docker"))
    await CategoryRepository.create(db_session, CategoryCreate(name="SQL"))

    rows = await CategoryRepository.list_all(db_session)
    assert [c.name for c in rows] == ["Python", "Docker", "SQL"]
    assert [c.id for c in rows] == sorted(c.id for c in rows)


async def test_update_mutates_only_set_fields(db_session):
    created = await CategoryRepository.create(
        db_session, CategoryCreate(name="Python", description="lang")
    )
    updated = await CategoryRepository.update(
        db_session, created, CategoryUpdate(name="Python 3")
    )
    assert updated.name == "Python 3"
    # description was not in the update payload (exclude_unset) — unchanged.
    assert updated.description == "lang"


async def test_delete_removes_row(db_session):
    created = await CategoryRepository.create(db_session, CategoryCreate(name="Temp"))
    await CategoryRepository.delete(db_session, created)
    assert await CategoryRepository.get_by_id(db_session, created.id) is None


async def test_link_skill_attaches_and_eager_loads(db_session):
    category = await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    skill = await _make_skill(db_session)

    linked = await CategoryRepository.link_skill(db_session, category, skill)
    assert [s.id for s in linked.skills] == [skill.id]


async def test_link_skill_is_idempotent(db_session):
    category = await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    skill = await _make_skill(db_session)

    first = await CategoryRepository.link_skill(db_session, category, skill)
    # Re-link the same skill — the unique (category, skill) constraint must not
    # be violated and the link count stays at one.
    second = await CategoryRepository.link_skill(db_session, first, skill)
    assert [s.id for s in second.skills] == [skill.id]


async def test_unlink_skill_detaches(db_session):
    category = await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    skill = await _make_skill(db_session)
    linked = await CategoryRepository.link_skill(db_session, category, skill)

    unlinked = await CategoryRepository.unlink_skill(db_session, linked, skill)
    assert unlinked.skills == []


async def test_unlink_skill_missing_link_is_idempotent(db_session):
    category = await CategoryRepository.create(db_session, CategoryCreate(name="Python"))
    skill = await _make_skill(db_session)
    # Skill was never linked — unlink must be a no-op, not an error.
    result = await CategoryRepository.unlink_skill(db_session, category, skill)
    assert result.skills == []


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Python"},
        {"name": "Docker", "description": "containers"},
    ],
)
def test_category_create_schema_accepts_valid(payload):
    model = CategoryCreate(**payload)
    assert model.name == payload["name"]


@pytest.mark.parametrize(
    "payload",
    [
        {},  # name is required
        {"description": "no name"},
    ],
)
def test_category_create_schema_rejects_missing_name(payload):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CategoryCreate(**payload)
