"""Unit tests for CategoryService.

No DB required — CategoryRepository / SkillRepository are patched with
AsyncMocks. The service methods are async; pytest-asyncio is not a CI
dependency, so each test drives them with asyncio.run().
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from src.schemas.category_schema import CategoryCreate, CategoryOut, CategoryUpdate
from src.services.category_service import CategoryService

REPO = "src.services.category_service.CategoryRepository"
SKILL_REPO = "src.services.category_service.SkillRepository"


def _category_row(category_id=1, name="Python", description=None, skills=()):
    return SimpleNamespace(
        id=category_id, name=name, description=description, skills=list(skills)
    )


def _skill_row(skill_id=1, name="FastAPI", description=None):
    return SimpleNamespace(id=skill_id, name=name, description=description)


@patch(f"{REPO}.create", new_callable=AsyncMock)
def test_create_category_returns_out_schema(mock_create):
    mock_create.return_value = _category_row()

    out = asyncio.run(CategoryService.create_category(None, CategoryCreate(name="Python")))

    assert isinstance(out, CategoryOut)
    assert out.id == 1
    assert out.name == "Python"
    assert out.skills == []


@patch(f"{REPO}.list_all", new_callable=AsyncMock)
def test_list_categories(mock_list):
    mock_list.return_value = [_category_row(1, "Python"), _category_row(2, "Docker")]

    out = asyncio.run(CategoryService.list_categories(None))

    assert [c.name for c in out] == ["Python", "Docker"]


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_get_category_includes_nested_skills(mock_get):
    mock_get.return_value = _category_row(skills=[_skill_row(7, "FastAPI")])

    out = asyncio.run(CategoryService.get_category_by_id(None, 1))

    assert len(out.skills) == 1
    assert out.skills[0].id == 7
    assert out.skills[0].name == "FastAPI"


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_get_category_missing_raises(mock_get):
    mock_get.return_value = None

    with pytest.raises(ValueError, match="Category not found"):
        asyncio.run(CategoryService.get_category_by_id(None, 99))


@patch(f"{REPO}.update", new_callable=AsyncMock)
@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_update_category(mock_get, mock_update):
    mock_get.return_value = _category_row()
    mock_update.return_value = _category_row(name="Python 3")

    out = asyncio.run(
        CategoryService.update_category(None, 1, CategoryUpdate(name="Python 3"))
    )

    assert out.name == "Python 3"
    mock_update.assert_awaited_once()


@patch(f"{REPO}.delete", new_callable=AsyncMock)
@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_delete_category_missing_raises(mock_get, mock_delete):
    mock_get.return_value = None

    with pytest.raises(ValueError, match="Category not found"):
        asyncio.run(CategoryService.delete_category(None, 99))
    mock_delete.assert_not_awaited()


@patch(f"{REPO}.link_skill", new_callable=AsyncMock)
@patch(f"{SKILL_REPO}.get_by_id", new_callable=AsyncMock)
@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_link_skill_returns_category_with_skill(mock_get, mock_skill_get, mock_link):
    mock_get.return_value = _category_row()
    mock_skill_get.return_value = _skill_row(7)
    mock_link.return_value = _category_row(skills=[_skill_row(7)])

    out = asyncio.run(CategoryService.link_skill(None, 1, 7))

    assert [s.id for s in out.skills] == [7]
    mock_link.assert_awaited_once()


@patch(f"{SKILL_REPO}.get_by_id", new_callable=AsyncMock)
@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_link_skill_missing_skill_raises(mock_get, mock_skill_get):
    mock_get.return_value = _category_row()
    mock_skill_get.return_value = None

    with pytest.raises(ValueError, match="Skill not found"):
        asyncio.run(CategoryService.link_skill(None, 1, 99))


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_link_skill_missing_category_raises(mock_get):
    mock_get.return_value = None

    with pytest.raises(ValueError, match="Category not found"):
        asyncio.run(CategoryService.link_skill(None, 99, 1))


@patch(f"{REPO}.unlink_skill", new_callable=AsyncMock)
@patch(f"{SKILL_REPO}.get_by_id", new_callable=AsyncMock)
@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_unlink_skill(mock_get, mock_skill_get, mock_unlink):
    mock_get.return_value = _category_row(skills=[_skill_row(7)])
    mock_skill_get.return_value = _skill_row(7)
    mock_unlink.return_value = _category_row()

    asyncio.run(CategoryService.unlink_skill(None, 1, 7))

    mock_unlink.assert_awaited_once()


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_list_category_skills(mock_get):
    mock_get.return_value = _category_row(skills=[_skill_row(7), _skill_row(8, "Docker")])

    out = asyncio.run(CategoryService.list_category_skills(None, 1))

    assert [s.id for s in out] == [7, 8]
