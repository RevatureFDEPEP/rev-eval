"""Tests for QuestionService.sample_by_skills validation (repo mocked, no Mongo)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.services.question_service import QuestionService

REPO = "src.services.question_service.QuestionRepository.sample_by_skills"


def test_empty_skills_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.sample_by_skills([], 5))
    assert exc.value.status_code == 400


def test_whitespace_only_skills_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.sample_by_skills(["  ", ""], 5))
    assert exc.value.status_code == 400


def test_invalid_type_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            QuestionService.sample_by_skills(["Python"], 5, question_type="bogus")
        )
    assert exc.value.status_code == 400


def test_invalid_difficulty_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            QuestionService.sample_by_skills(["Python"], 5, difficulty="impossible")
        )
    assert exc.value.status_code == 400


def test_valid_request_passes_cleaned_skills_to_repo():
    with patch(REPO, new=AsyncMock(return_value=["q1"])) as mock_repo:
        result = asyncio.run(QuestionService.sample_by_skills([" Python ", "SQL"], 3))
    assert result == ["q1"]
    mock_repo.assert_awaited_once_with(["Python", "SQL"], 3, None, None)
