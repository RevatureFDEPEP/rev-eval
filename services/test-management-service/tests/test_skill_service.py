"""Unit tests for SkillService.

No DB required — SkillRepository is patched with AsyncMocks. The service
methods are async; pytest-asyncio is not a CI dependency, so each test drives
them with asyncio.run().
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from src.schemas.skill_schema import SkillCreate, SkillOut
from src.services.skill_service import SkillService

REPO = "src.services.skill_service.SkillRepository"


def _skill_row(skill_id=1, name="FastAPI", description=None):
    return SimpleNamespace(id=skill_id, name=name, description=description)


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_get_skill_by_id_returns_out_schema(mock_get):
    mock_get.return_value = _skill_row(7, "FastAPI")

    out = asyncio.run(SkillService.get_skill_by_id(None, 7))

    assert isinstance(out, SkillOut)
    assert out.id == 7
    assert out.name == "FastAPI"


@patch(f"{REPO}.get_by_id", new_callable=AsyncMock)
def test_get_skill_by_id_missing_raises(mock_get):
    mock_get.return_value = None

    with pytest.raises(ValueError, match="Skill not found"):
        asyncio.run(SkillService.get_skill_by_id(None, 99))


@patch(f"{REPO}.create", new_callable=AsyncMock)
def test_create_skill_returns_out_schema(mock_create):
    mock_create.return_value = _skill_row(1, "Python")

    out = asyncio.run(SkillService.create_skill(None, SkillCreate(name="Python")))

    assert isinstance(out, SkillOut)
    assert out.id == 1
    assert out.name == "Python"


@patch(f"{REPO}.list_all", new_callable=AsyncMock)
def test_list_skills(mock_list):
    mock_list.return_value = [_skill_row(1, "Python"), _skill_row(2, "Docker")]

    out = asyncio.run(SkillService.list_skills(None))

    assert [s.name for s in out] == ["Python", "Docker"]
