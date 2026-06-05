import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.models.question import QuestionType
from src.schemas.question import QuestionCreate

# --- Settings.mongo_url ---


def test_mongo_url_prefers_uri():
    s = Settings(SERVICE_NAME="q", MONGO_URI="mongodb://localhost:27017/test")
    assert s.mongo_url == "mongodb://localhost:27017/test"


def test_mongo_url_assembles_srv():
    s = Settings(
        SERVICE_NAME="q",
        MONGO_USER="user",
        MONGODB_PASSWORD="pass",
        MONGO_CLUSTER="cluster0.abc.mongodb.net",
    )
    url = s.mongo_url
    assert url.startswith("mongodb+srv://")
    assert "cluster0.abc.mongodb.net" in url


def test_mongo_url_missing_config_raises():
    s = Settings(SERVICE_NAME="q")
    with pytest.raises(ValueError, match="MongoDB connection not configured"):
        _ = s.mongo_url


# --- Settings.cors_origins ---


def test_cors_origins_wildcard():
    s = Settings(SERVICE_NAME="q", ALLOW_ORIGINS="*")
    assert s.cors_origins == ["*"]


def test_cors_origins_split():
    s = Settings(SERVICE_NAME="q", ALLOW_ORIGINS="http://a.com,http://b.com")
    assert s.cors_origins == ["http://a.com", "http://b.com"]


def test_cors_origins_single():
    s = Settings(SERVICE_NAME="q", ALLOW_ORIGINS="http://localhost:3000")
    assert s.cors_origins == ["http://localhost:3000"]


# --- QuestionType enum ---


def test_question_type_mcq_value():
    assert QuestionType.MCQ == "mcq"


def test_question_type_text_value():
    assert QuestionType.TEXT == "text"


def test_question_type_multi_value():
    assert QuestionType.MULTI == "multi"


def test_question_type_true_false_value():
    assert QuestionType.TRUE_FALSE == "true_false"


def test_question_type_membership():
    assert "mcq" in QuestionType


# --- QuestionCreate validation ---


def test_question_create_valid_text_type():
    q = QuestionCreate(
        type=QuestionType.TEXT,
        question_text="What is the purpose of Docker containers in microservices?",
        sample_answer="They provide isolated, reproducible runtime environments.",
    )
    assert q.type == QuestionType.TEXT
    assert q.difficulty == "medium"


def test_question_create_text_too_short():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TEXT,
            question_text="Short",
        )


def test_question_create_invalid_difficulty():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TEXT,
            question_text="What is the purpose of Docker containers in microservices?",
            difficulty="impossible",
        )


def test_question_create_default_difficulty():
    q = QuestionCreate(
        type=QuestionType.TEXT,
        question_text="What is the purpose of Docker containers in microservices?",
        sample_answer="They provide isolated, reproducible runtime environments.",
    )
    assert q.difficulty == "medium"


# --- MCQ validation ---

_MCQ_OPTIONS = [
    {"text": "Option A"},
    {"text": "Option B"},
    {"text": "Option C"},
]


def test_question_create_valid_mcq():
    q = QuestionCreate(
        type=QuestionType.MCQ,
        question_text="Which command builds a Docker image from a Dockerfile?",
        options=_MCQ_OPTIONS,
        correct_answers=[1],
    )
    assert q.type == QuestionType.MCQ


def test_question_create_mcq_no_options_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which command builds a Docker image from a Dockerfile?",
            correct_answers=[1],
        )


def test_question_create_mcq_multiple_answers_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which command builds a Docker image from a Dockerfile?",
            options=_MCQ_OPTIONS,
            correct_answers=[1, 2],
        )


def test_question_create_mcq_out_of_range_answer_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which command builds a Docker image from a Dockerfile?",
            options=_MCQ_OPTIONS,
            correct_answers=[99],
        )


# --- MULTI validation ---


def test_question_create_valid_multi():
    q = QuestionCreate(
        type=QuestionType.MULTI,
        question_text="Which of the following are valid Docker networking modes?",
        options=_MCQ_OPTIONS,
        correct_answers=[1, 2],
    )
    assert q.type == QuestionType.MULTI


def test_question_create_multi_all_correct_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MULTI,
            question_text="Which of the following are valid Docker networking modes?",
            options=_MCQ_OPTIONS,
            correct_answers=[1, 2, 3],
        )


def test_question_create_multi_non_int_answers_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MULTI,
            question_text="Which of the following are valid Docker networking modes?",
            options=_MCQ_OPTIONS,
            correct_answers=["a", "b"],
        )


# --- TRUE_FALSE validation ---


def test_question_create_valid_true_false():
    q = QuestionCreate(
        type=QuestionType.TRUE_FALSE,
        question_text="Docker containers share the host OS kernel with the host machine.",
        correct_answers=[True],
    )
    assert q.type == QuestionType.TRUE_FALSE


def test_question_create_true_false_with_options_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TRUE_FALSE,
            question_text="Docker containers share the host OS kernel with the host machine.",
            options=_MCQ_OPTIONS,
            correct_answers=[True],
        )


def test_question_create_true_false_non_bool_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TRUE_FALSE,
            question_text="Docker containers share the host OS kernel with the host machine.",
            correct_answers=[1],
        )


# --- Options field validation ---


def test_question_create_options_too_few_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which command builds a Docker image from a Dockerfile?",
            options=[{"text": "Only one"}],
            correct_answers=[1],
        )


def test_question_create_options_duplicate_text_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which command builds a Docker image from a Dockerfile?",
            options=[{"text": "Same"}, {"text": "Same"}],
            correct_answers=[1],
        )


# --- Skills / tags validation ---


def test_question_create_skills_valid():
    q = QuestionCreate(
        type=QuestionType.TEXT,
        question_text="What is the purpose of Docker containers in microservices?",
        sample_answer="They provide isolated, reproducible runtime environments.",
        skills=["Docker", "DevOps"],
    )
    assert q.skills == ["Docker", "DevOps"]


def test_question_create_skills_duplicate_raises():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TEXT,
            question_text="What is the purpose of Docker containers in microservices?",
            sample_answer="They provide isolated, reproducible runtime environments.",
            skills=["Docker", "Docker"],
        )
