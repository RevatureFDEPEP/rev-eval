"""Validator coverage for QuestionCreate / QuestionUpdate / QuestionResponse.

Pure Pydantic — no Mongo, no service. Exercises the type-specific model
validators and the field validators (text/skills/tags/options) that the
question authoring API relies on.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.question import QuestionCreate, QuestionResponse, QuestionUpdate

OPTS2 = [{"text": "Alpha"}, {"text": "Beta"}]
OPTS3 = [{"text": "Alpha"}, {"text": "Beta"}, {"text": "Gamma"}]
TEXT = "A sufficiently long question text"


# ----- valid construction (happy paths) -----------------------------------


def test_valid_mcq():
    q = QuestionCreate(
        type="mcq", question_text=TEXT, options=OPTS2, correct_answers=[1]
    )
    assert q.type == "mcq"
    assert q.difficulty == "medium"  # default


def test_valid_multi():
    q = QuestionCreate(
        type="multi", question_text=TEXT, options=OPTS3, correct_answers=[1, 2]
    )
    assert q.correct_answers == [1, 2]


def test_valid_true_false():
    q = QuestionCreate(type="true_false", question_text=TEXT, correct_answers=[True])
    assert q.correct_answers == [True]


def test_valid_text_question():
    q = QuestionCreate(
        type="text", question_text=TEXT, sample_answer="This is a model answer."
    )
    assert q.sample_answer.startswith("This")


# ----- field validators ----------------------------------------------------


def test_question_text_stripped_below_min_rejected():
    # passes the raw min_length=10 but strips to < 10 -> custom validator fires
    with pytest.raises(ValidationError):
        QuestionCreate(type="text", question_text="  abcdefg  ", sample_answer=TEXT)


def test_duplicate_skills_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="text",
            question_text=TEXT,
            sample_answer=TEXT,
            skills=["Python", "Python"],
        )


def test_skills_whitespace_stripped_and_deduped_ok():
    q = QuestionCreate(
        type="text", question_text=TEXT, sample_answer=TEXT, skills=[" Python ", "SQL"]
    )
    assert q.skills == ["Python", "SQL"]


def test_duplicate_tags_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="text", question_text=TEXT, sample_answer=TEXT, tags=["a", "a"]
        )


def test_too_few_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq",
            question_text=TEXT,
            options=[{"text": "only"}],
            correct_answers=[1],
        )


def test_too_many_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq",
            question_text=TEXT,
            options=[{"text": f"opt{i}"} for i in range(11)],
            correct_answers=[1],
        )


def test_duplicate_option_text_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq",
            question_text=TEXT,
            options=[{"text": "Paris"}, {"text": "paris"}],
            correct_answers=[1],
        )


# ----- model validator: MCQ -------------------------------------------------


def test_mcq_without_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="mcq", question_text=TEXT, correct_answers=[1])


def test_mcq_without_correct_answers_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="mcq", question_text=TEXT, options=OPTS2)


def test_mcq_multiple_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq", question_text=TEXT, options=OPTS2, correct_answers=[1, 2]
        )


def test_mcq_non_int_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq", question_text=TEXT, options=OPTS2, correct_answers=["x"]
        )


def test_mcq_out_of_range_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="mcq", question_text=TEXT, options=OPTS2, correct_answers=[5]
        )


# ----- model validator: MULTI -----------------------------------------------


def test_multi_without_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="multi", question_text=TEXT, correct_answers=[1])


def test_multi_without_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="multi", question_text=TEXT, options=OPTS3, correct_answers=[]
        )


def test_multi_non_int_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="multi", question_text=TEXT, options=OPTS3, correct_answers=[1, "x"]
        )


def test_multi_out_of_range_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="multi", question_text=TEXT, options=OPTS3, correct_answers=[9]
        )


def test_multi_duplicate_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="multi", question_text=TEXT, options=OPTS3, correct_answers=[1, 1]
        )


def test_multi_all_options_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="multi", question_text=TEXT, options=OPTS2, correct_answers=[1, 2]
        )


# ----- model validator: TRUE_FALSE & TEXT -----------------------------------


def test_true_false_with_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="true_false", question_text=TEXT, options=OPTS2, correct_answers=[True]
        )


def test_true_false_without_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="true_false", question_text=TEXT)


def test_true_false_multiple_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="true_false", question_text=TEXT, correct_answers=[True, False]
        )


def test_true_false_non_bool_correct_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="true_false", question_text=TEXT, correct_answers=["yes"])


def test_text_with_options_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="text", question_text=TEXT, options=OPTS2, sample_answer=TEXT
        )


def test_text_with_correct_answers_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(
            type="text", question_text=TEXT, correct_answers=[1], sample_answer=TEXT
        )


def test_text_without_sample_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="text", question_text=TEXT)


def test_text_short_sample_rejected():
    with pytest.raises(ValidationError):
        QuestionCreate(type="text", question_text=TEXT, sample_answer="short")


# ----- QuestionUpdate -------------------------------------------------------


def test_update_all_none_is_valid():
    u = QuestionUpdate()
    assert u.question_text is None


def test_update_question_text_stripped_below_min_rejected():
    with pytest.raises(ValidationError):
        QuestionUpdate(question_text="  abcdefg  ")


def test_update_duplicate_skills_rejected():
    with pytest.raises(ValidationError):
        QuestionUpdate(skills=["x", "x"])


def test_update_duplicate_tags_rejected():
    with pytest.raises(ValidationError):
        QuestionUpdate(tags=["t", "t"])


def test_update_too_few_options_rejected():
    with pytest.raises(ValidationError):
        QuestionUpdate(options=[{"text": "only"}])


def test_update_duplicate_option_text_rejected():
    with pytest.raises(ValidationError):
        QuestionUpdate(options=[{"text": "Paris"}, {"text": "PARIS"}])


def test_update_consistency_out_of_range_rejected():
    # both options and correct_answers given -> consistency check fires
    with pytest.raises(ValidationError):
        QuestionUpdate(options=OPTS2, correct_answers=[5])


def test_update_consistency_valid():
    u = QuestionUpdate(options=OPTS2, correct_answers=[1])
    assert u.correct_answers == [1]


# ----- QuestionResponse -----------------------------------------------------


def test_question_response_accepts_mongo_id_alias():
    now = datetime.now(UTC)
    resp = QuestionResponse(
        _id="abc123",
        type="mcq",
        question_text=TEXT,
        created_at=now,
        updated_at=now,
    )
    assert resp.id == "abc123"
    assert resp.difficulty == "medium"
