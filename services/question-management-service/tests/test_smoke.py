"""Smoke / sanity tests for question-management-service.

No Mongo required. These cover the QuestionType enum, the settings helpers
(cors_origins parsing + mongo_url resolution), and type-aware QuestionCreate
validation.
"""
import pytest
from pydantic import ValidationError
from src.config.settings import Settings, settings
from src.models.question import QuestionType
from src.schemas.question import QuestionCreate


def test_question_type_values():
    assert {t.value for t in QuestionType} == {"mcq", "multi", "true_false", "text"}


def test_cors_origins_wildcard():
    s = Settings(SERVICE_NAME="x", ALLOW_ORIGINS="*", MONGO_URI="mongodb://localhost:27017/db")
    assert s.cors_origins == ["*"]


def test_cors_origins_csv_is_split_and_stripped():
    s = Settings(
        SERVICE_NAME="x",
        ALLOW_ORIGINS="http://a, http://b",
        MONGO_URI="mongodb://localhost:27017/db",
    )
    assert s.cors_origins == ["http://a", "http://b"]


def test_mongo_url_prefers_uri():
    assert settings.mongo_url == "mongodb://localhost:27017/evalai"


def test_mongo_url_unconfigured_raises():
    s = Settings(
        SERVICE_NAME="x",
        MONGO_URI=None,
        MONGO_USER=None,
        MONGODB_PASSWORD=None,
        MONGO_CLUSTER=None,
    )
    with pytest.raises(ValueError):
        _ = s.mongo_url


def test_question_create_valid_text():
    q = QuestionCreate(
        type=QuestionType.TEXT,
        question_text="What is dependency injection?",
        sample_answer="A pattern for supplying collaborators.",
    )
    assert q.type == QuestionType.TEXT
    assert q.difficulty == "medium"


def test_question_text_too_short_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type=QuestionType.TEXT, question_text="short")
