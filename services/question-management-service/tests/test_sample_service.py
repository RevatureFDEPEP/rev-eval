"""Unit tests for the quiz-sampling pure helpers (W3-F1, Part A).

SYNC only — these import *only* ``src.services.sample_service`` (no FastAPI app,
no route module, no Beanie/Mongo model), so the suite needs nothing beyond
pytest + the service requirements and the route/model code stays out of the
coverage denominator. They lock down:
- the ``$sample`` pipeline shape + the optional ``$match`` skill filter;
- size clamping (default / floor / ceiling);
- comma-separated skill parsing;
- the quiz-safe projection that strips the answer key.
"""

import pytest
from src.schemas.sample import QuizSampleQuestion
from src.services.sample_service import (
    DEFAULT_SAMPLE_SIZE,
    MAX_SAMPLE_SIZE,
    build_sample_pipeline,
    map_question_to_sample,
    normalize_sample_size,
    parse_skills,
)

# ---------------------------------------------------------------------------
# normalize_sample_size
# ---------------------------------------------------------------------------


def test_normalize_size_none_uses_default():
    assert normalize_sample_size(None) == DEFAULT_SAMPLE_SIZE


@pytest.mark.parametrize("n", [1, 5, 20, 199, MAX_SAMPLE_SIZE])
def test_normalize_size_passthrough_in_range(n):
    assert normalize_sample_size(n) == n


@pytest.mark.parametrize("n", [0, -1, -1000])
def test_normalize_size_floor_is_one(n):
    assert normalize_sample_size(n) == 1


def test_normalize_size_capped_at_ceiling():
    assert normalize_sample_size(MAX_SAMPLE_SIZE + 1) == MAX_SAMPLE_SIZE
    assert normalize_sample_size(10_000) == MAX_SAMPLE_SIZE


# ---------------------------------------------------------------------------
# parse_skills
# ---------------------------------------------------------------------------


def test_parse_skills_none_is_empty():
    assert parse_skills(None) == []


def test_parse_skills_empty_string_is_empty():
    assert parse_skills("") == []


def test_parse_skills_single():
    assert parse_skills("python") == ["python"]


def test_parse_skills_strips_and_drops_blanks():
    assert parse_skills("python, , sql,") == ["python", "sql"]


def test_parse_skills_whitespace_only_is_empty():
    assert parse_skills("  ,  ,") == []


# ---------------------------------------------------------------------------
# build_sample_pipeline
# ---------------------------------------------------------------------------


def test_pipeline_no_skills_is_sample_only():
    pipeline = build_sample_pipeline(20, None)
    assert pipeline == [{"$sample": {"size": 20}}]


def test_pipeline_with_skills_prepends_match():
    pipeline = build_sample_pipeline(5, "python,sql")
    assert pipeline == [
        {"$match": {"skills": {"$in": ["python", "sql"]}}},
        {"$sample": {"size": 5}},
    ]


def test_pipeline_default_size_when_n_none():
    pipeline = build_sample_pipeline(None, None)
    assert pipeline == [{"$sample": {"size": DEFAULT_SAMPLE_SIZE}}]


def test_pipeline_size_is_clamped():
    pipeline = build_sample_pipeline(10_000, None)
    assert pipeline[-1] == {"$sample": {"size": MAX_SAMPLE_SIZE}}


def test_pipeline_blank_skills_does_not_add_match():
    pipeline = build_sample_pipeline(3, "  ,  ")
    assert pipeline == [{"$sample": {"size": 3}}]


# ---------------------------------------------------------------------------
# map_question_to_sample  (answer-key safety)
# ---------------------------------------------------------------------------


def test_map_returns_only_quiz_safe_fields():
    doc = {
        "_id": "abc123",
        "question_text": "What is 2 + 2?",
        "type": "mcq",
        "difficulty": "easy",
        "options": [
            {"option_id": 1, "text": "3"},
            {"option_id": 2, "text": "4"},
        ],
        "correct_answers": [2],
        "sample_answer": "the answer is 4",
        "answer_explanation": "basic arithmetic",
    }
    out = map_question_to_sample(doc)
    assert set(out) == {"_id", "question_text", "type", "difficulty", "options"}


def test_map_never_leaks_correct_answers():
    doc = {
        "_id": "x",
        "question_text": "q",
        "type": "multi",
        "difficulty": "hard",
        "options": [{"option_id": 1, "text": "a"}, {"option_id": 2, "text": "b"}],
        "correct_answers": [1, 2],
        "sample_answer": "secret",
    }
    out = map_question_to_sample(doc)
    assert "correct_answers" not in out
    assert "sample_answer" not in out
    assert "answer_explanation" not in out


def test_map_stringifies_id():
    out = map_question_to_sample({"_id": 12345, "question_text": "q"})
    assert out["_id"] == "12345"
    assert isinstance(out["_id"], str)


def test_map_options_none_for_answerless_type():
    doc = {
        "_id": "tf",
        "question_text": "The sky is blue.",
        "type": "true_false",
        "difficulty": "easy",
        "options": None,
        "correct_answers": [True],
    }
    out = map_question_to_sample(doc)
    assert out["options"] is None


def test_map_normalizes_dict_options_to_id_and_text_only():
    doc = {
        "_id": "1",
        "question_text": "q",
        "type": "mcq",
        "difficulty": "medium",
        # an option dict carrying an extra field must not pass it through
        "options": [{"option_id": 1, "text": "a", "is_correct": True}],
    }
    out = map_question_to_sample(doc)
    assert out["options"] == [{"option_id": 1, "text": "a"}]


def test_map_normalizes_object_options():
    class Opt:
        def __init__(self, option_id, text):
            self.option_id = option_id
            self.text = text

    doc = {
        "_id": "1",
        "question_text": "q",
        "type": "mcq",
        "difficulty": "medium",
        "options": [Opt(1, "a"), Opt(2, "b")],
    }
    out = map_question_to_sample(doc)
    assert out["options"] == [
        {"option_id": 1, "text": "a"},
        {"option_id": 2, "text": "b"},
    ]


def test_map_missing_fields_become_none():
    out = map_question_to_sample({"_id": "only"})
    assert out["question_text"] is None
    assert out["type"] is None
    assert out["difficulty"] is None
    assert out["options"] is None


# ---------------------------------------------------------------------------
# QuizSampleQuestion response_model  (STRUCTURAL answer-key guard)
# ---------------------------------------------------------------------------
# The /sample route declares ``response_model=list[QuizSampleQuestion]``; these
# tests lock the model so the answer-key omission is enforced by the type even
# if the hand-built dict ever regresses.


def test_response_model_drops_answer_key_fields():
    """Constructing the response model from a dict that *carries* the answer key
    must not surface it: extra fields are ignored and never serialized out."""
    raw = {
        "_id": "abc123",
        "question_text": "What is 2 + 2?",
        "type": "mcq",
        "difficulty": "easy",
        "options": [{"option_id": 1, "text": "4"}],
        "correct_answers": [1],
        "sample_answer": "4",
        "answer_explanation": "arithmetic",
    }
    model = QuizSampleQuestion.model_validate(raw)
    # by_alias mirrors how FastAPI serializes the response over the wire.
    dumped = model.model_dump(by_alias=True)
    assert set(dumped) == {"_id", "question_text", "type", "difficulty", "options"}
    assert "correct_answers" not in dumped
    assert "sample_answer" not in dumped
    assert "answer_explanation" not in dumped


def test_response_model_validates_the_mapped_dict():
    """The shape produced by ``map_question_to_sample`` validates cleanly and
    round-trips back to the ``_id`` alias the frontend consumes."""
    mapped = map_question_to_sample(
        {
            "_id": 999,
            "question_text": "q",
            "type": "mcq",
            "difficulty": "medium",
            "options": [{"option_id": 1, "text": "a"}, {"option_id": 2, "text": "b"}],
            "correct_answers": [1],
        }
    )
    model = QuizSampleQuestion.model_validate(mapped)
    dumped = model.model_dump(by_alias=True)
    assert dumped["_id"] == "999"
    assert dumped["question_text"] == "q"
    assert dumped["options"] == [
        {"option_id": 1, "text": "a"},
        {"option_id": 2, "text": "b"},
    ]


def test_response_model_requires_id():
    """``_id`` is the one required field — a sampled doc must be identifiable."""
    with pytest.raises(ValueError):
        QuizSampleQuestion.model_validate({"question_text": "no id"})
