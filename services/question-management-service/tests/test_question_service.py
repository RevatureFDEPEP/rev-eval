"""
Tests for question-management-service schema validation.

MongoDB-dependent code (routes, services, repository) cannot be tested
without a live MongoDB instance. These tests cover pure Pydantic schema
validation which requires no external services.
"""
import os
import pytest
from pydantic import ValidationError

# Provide required env vars before any src imports that pull in settings
os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("PORT", "8003")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

from src.models.question import OptionCreate, Option, QuestionType
from src.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    SingleSelectPayload,
    MultiSelectPayload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mcq_opts(n=2):
    return [OptionCreate(text=f"Option {i}") for i in range(1, n + 1)]


def make_mcq(**kwargs):
    defaults = dict(
        type=QuestionType.MCQ,
        question_text="What is the capital of France?",
        options=mcq_opts(4),
        correct_answers=[2],
        skills=["Geography"],
    )
    defaults.update(kwargs)
    return QuestionCreate(**defaults)


def make_multi(**kwargs):
    defaults = dict(
        type=QuestionType.MULTI,
        question_text="Which of the following are prime numbers?",
        options=mcq_opts(4),
        correct_answers=[1, 3],
        skills=["Math"],
    )
    defaults.update(kwargs)
    return QuestionCreate(**defaults)


def make_true_false(**kwargs):
    defaults = dict(
        type=QuestionType.TRUE_FALSE,
        question_text="The sky is blue. True or False?",
        correct_answers=[True],
        skills=["Science"],
    )
    defaults.update(kwargs)
    return QuestionCreate(**defaults)


def make_text(**kwargs):
    defaults = dict(
        type=QuestionType.TEXT,
        question_text="Explain what a Python decorator is.",
        sample_answer="A decorator is a function that wraps another function to extend its behavior.",
        skills=["Python"],
    )
    defaults.update(kwargs)
    return QuestionCreate(**defaults)


# ---------------------------------------------------------------------------
# QuestionType enum
# ---------------------------------------------------------------------------

class TestQuestionTypeEnum:
    def test_all_values(self):
        assert QuestionType.MCQ.value == "mcq"
        assert QuestionType.MULTI.value == "multi"
        assert QuestionType.TRUE_FALSE.value == "true_false"
        assert QuestionType.TEXT.value == "text"


# ---------------------------------------------------------------------------
# OptionCreate model
# ---------------------------------------------------------------------------

class TestOptionCreate:
    def test_valid_option(self):
        opt = OptionCreate(text="Paris")
        assert opt.text == "Paris"

    def test_strips_whitespace(self):
        opt = OptionCreate(text="  London  ")
        assert opt.text == "London"

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            OptionCreate(text="   ")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            OptionCreate(text="x" * 501)


# ---------------------------------------------------------------------------
# Option model (stored version with option_id)
# ---------------------------------------------------------------------------

class TestOption:
    def test_valid_option(self):
        opt = Option(option_id=1, text="Paris")
        assert opt.option_id == 1
        assert opt.text == "Paris"

    def test_option_id_must_be_at_least_1(self):
        with pytest.raises(ValidationError):
            Option(option_id=0, text="Paris")


# ---------------------------------------------------------------------------
# QuestionCreate — question_text validation
# ---------------------------------------------------------------------------

class TestQuestionCreateText:
    def test_valid_question_text(self):
        q = make_mcq()
        assert q.question_text == "What is the capital of France?"

    def test_strips_leading_trailing_whitespace(self):
        q = make_mcq(question_text="  What is the capital of France?  ")
        assert not q.question_text.startswith(" ")

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(question_text="Short?")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(question_text="x" * 2001)


# ---------------------------------------------------------------------------
# QuestionCreate — skills validation
# ---------------------------------------------------------------------------

class TestQuestionCreateSkills:
    def test_valid_skills(self):
        q = make_mcq(skills=["Python", "Django"])
        assert q.skills == ["Python", "Django"]

    def test_empty_skills_allowed(self):
        q = make_mcq(skills=[])
        assert q.skills == []

    def test_strips_skill_whitespace(self):
        q = make_mcq(skills=["  Python  ", "Django"])
        assert "Python" in q.skills

    def test_duplicate_skills_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            make_mcq(skills=["Python", "Python"])

    def test_too_many_skills_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(skills=[f"Skill{i}" for i in range(21)])

    def test_empty_strings_filtered_out(self):
        q = make_mcq(skills=["Python", ""])
        assert "" not in q.skills


# ---------------------------------------------------------------------------
# QuestionCreate — tags validation
# ---------------------------------------------------------------------------

class TestQuestionCreateTags:
    def test_valid_tags(self):
        q = make_mcq(tags=["geography", "capitals"])
        assert q.tags == ["geography", "capitals"]

    def test_empty_tags_allowed(self):
        q = make_mcq(tags=[])
        assert q.tags == []

    def test_duplicate_tags_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            make_mcq(tags=["python", "python"])

    def test_too_many_tags_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(tags=[f"tag{i}" for i in range(31)])


# ---------------------------------------------------------------------------
# QuestionCreate — options validation
# ---------------------------------------------------------------------------

class TestQuestionCreateOptions:
    def test_too_few_options_raises(self):
        with pytest.raises(ValidationError, match="2 options"):
            make_mcq(options=[OptionCreate(text="Only one")])

    def test_too_many_options_raises(self):
        with pytest.raises(ValidationError, match="Maximum 10"):
            make_mcq(options=mcq_opts(11))

    def test_empty_option_text_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(options=[OptionCreate(text="Valid"), OptionCreate(text="   ")])

    def test_duplicate_option_text_raises(self):
        with pytest.raises(ValidationError, match="duplicate"):
            make_mcq(options=[OptionCreate(text="Same"), OptionCreate(text="same")])


# ---------------------------------------------------------------------------
# QuestionCreate — MCQ type validation
# ---------------------------------------------------------------------------

class TestQuestionCreateMcq:
    def test_valid_mcq(self):
        q = make_mcq()
        assert q.type == QuestionType.MCQ

    def test_mcq_no_options_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(options=None)

    def test_mcq_no_correct_answers_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(correct_answers=None)

    def test_mcq_multiple_correct_answers_raises(self):
        with pytest.raises(ValidationError, match="exactly one"):
            make_mcq(correct_answers=[1, 2])

    def test_mcq_non_int_correct_answer_raises(self):
        # bool is subclass of int in Python, so use a string to trigger the type check
        with pytest.raises(ValidationError, match="integer"):
            make_mcq(correct_answers=["first_option"])

    def test_mcq_correct_answer_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(options=mcq_opts(2), correct_answers=[5])

    def test_mcq_correct_answer_zero_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(options=mcq_opts(2), correct_answers=[0])

    def test_mcq_with_difficulty(self):
        q = make_mcq(difficulty="hard")
        assert q.difficulty == "hard"

    def test_mcq_invalid_difficulty_raises(self):
        with pytest.raises(ValidationError):
            make_mcq(difficulty="extreme")


# ---------------------------------------------------------------------------
# QuestionCreate — MULTI type validation
# ---------------------------------------------------------------------------

class TestQuestionCreateMulti:
    def test_valid_multi(self):
        q = make_multi()
        assert q.type == QuestionType.MULTI
        assert q.correct_answers == [1, 3]

    def test_multi_no_options_raises(self):
        with pytest.raises(ValidationError):
            make_multi(options=None)

    def test_multi_empty_correct_answers_raises(self):
        with pytest.raises(ValidationError):
            make_multi(correct_answers=[])

    def test_multi_non_int_correct_answers_raises(self):
        with pytest.raises(ValidationError, match="integers"):
            make_multi(correct_answers=["a", "b"])

    def test_multi_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            make_multi(options=mcq_opts(3), correct_answers=[1, 99])

    def test_multi_duplicate_correct_answers_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            make_multi(options=mcq_opts(4), correct_answers=[1, 1])

    def test_multi_all_options_correct_raises(self):
        with pytest.raises(ValidationError, match="all options"):
            make_multi(options=mcq_opts(2), correct_answers=[1, 2])


# ---------------------------------------------------------------------------
# QuestionCreate — TRUE_FALSE type validation
# ---------------------------------------------------------------------------

class TestQuestionCreateTrueFalse:
    def test_valid_true_answer(self):
        q = make_true_false(correct_answers=[True])
        assert q.correct_answers == [True]

    def test_valid_false_answer(self):
        q = make_true_false(correct_answers=[False])
        assert q.correct_answers == [False]

    def test_true_false_with_options_raises(self):
        with pytest.raises(ValidationError, match="should not have options"):
            make_true_false(options=mcq_opts(2))

    def test_true_false_no_correct_answers_raises(self):
        with pytest.raises(ValidationError):
            make_true_false(correct_answers=None)

    def test_true_false_multiple_answers_raises(self):
        with pytest.raises(ValidationError, match="exactly one"):
            make_true_false(correct_answers=[True, False])

    def test_true_false_non_bool_raises(self):
        with pytest.raises(ValidationError, match="boolean"):
            make_true_false(correct_answers=[1])


# ---------------------------------------------------------------------------
# QuestionCreate — TEXT type validation
# ---------------------------------------------------------------------------

class TestQuestionCreateText2:
    def test_valid_text_question(self):
        q = make_text()
        assert q.sample_answer is not None

    def test_text_with_options_raises(self):
        with pytest.raises(ValidationError, match="should not have options"):
            make_text(options=mcq_opts(2))

    def test_text_with_correct_answers_raises(self):
        with pytest.raises(ValidationError, match="should not have correct_answers"):
            make_text(correct_answers=["answer"])

    def test_text_no_sample_answer_raises(self):
        with pytest.raises(ValidationError, match="sample_answer"):
            make_text(sample_answer=None)

    def test_text_blank_sample_answer_raises(self):
        with pytest.raises(ValidationError, match="sample_answer"):
            make_text(sample_answer="   ")

    def test_text_short_sample_answer_raises(self):
        with pytest.raises(ValidationError, match="10 characters"):
            make_text(sample_answer="Too short")


# ---------------------------------------------------------------------------
# QuestionUpdate validation
# ---------------------------------------------------------------------------

class TestQuestionUpdate:
    def test_all_none_fields_allowed(self):
        upd = QuestionUpdate()
        assert upd.question_text is None
        assert upd.options is None

    def test_valid_question_text_update(self):
        upd = QuestionUpdate(question_text="Updated question text here")
        assert upd.question_text == "Updated question text here"

    def test_short_question_text_raises(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(question_text="Short")

    def test_none_question_text_allowed(self):
        upd = QuestionUpdate(question_text=None)
        assert upd.question_text is None

    def test_duplicate_skills_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            QuestionUpdate(skills=["Python", "Python"])

    def test_too_many_skills_raises(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(skills=[f"Skill{i}" for i in range(21)])

    def test_none_skills_allowed(self):
        upd = QuestionUpdate(skills=None)
        assert upd.skills is None

    def test_duplicate_tags_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            QuestionUpdate(tags=["python", "python"])

    def test_too_few_options_raises(self):
        with pytest.raises(ValidationError, match="2 options"):
            QuestionUpdate(options=[OptionCreate(text="Only one")])

    def test_duplicate_option_text_raises(self):
        with pytest.raises(ValidationError, match="duplicate"):
            QuestionUpdate(options=[OptionCreate(text="Same"), OptionCreate(text="same")])

    def test_none_options_allowed(self):
        upd = QuestionUpdate(options=None)
        assert upd.options is None

    def test_consistent_options_and_correct_answers(self):
        opts = [OptionCreate(text=f"Opt {i}") for i in range(3)]
        upd = QuestionUpdate(options=opts, correct_answers=[1])
        assert upd.correct_answers == [1]

    def test_correct_answers_out_of_option_range_raises(self):
        opts = [OptionCreate(text=f"Opt {i}") for i in range(2)]
        with pytest.raises(ValidationError):
            QuestionUpdate(options=opts, correct_answers=[5])


# ---------------------------------------------------------------------------
# SingleSelectPayload (MCQ discriminated union)
# ---------------------------------------------------------------------------

class TestSingleSelectPayload:
    def _make(self, **kwargs):
        defaults = dict(
            question_type="mcq",
            question_text="Which city is the capital of France?",
            options=[OptionCreate(text=f"City{i}") for i in range(3)],
            correct_answer=2,
        )
        defaults.update(kwargs)
        return SingleSelectPayload(**defaults)

    def test_valid_payload(self):
        p = self._make()
        assert p.question_type == "mcq"
        assert p.correct_answer == 2

    def test_answer_exceeds_option_count_raises(self):
        with pytest.raises(ValidationError, match="exceeds option count"):
            self._make(
                options=[OptionCreate(text="Only one"), OptionCreate(text="Two")],
                correct_answer=5,
            )

    def test_answer_below_1_raises(self):
        with pytest.raises(ValidationError):
            self._make(correct_answer=0)

    def test_too_few_options_raises(self):
        with pytest.raises(ValidationError):
            self._make(options=[OptionCreate(text="Only one")])

    def test_too_many_options_raises(self):
        with pytest.raises(ValidationError):
            self._make(options=[OptionCreate(text=f"Opt{i}") for i in range(11)])

    def test_short_question_text_raises(self):
        with pytest.raises(ValidationError):
            self._make(question_text="Short?")


# ---------------------------------------------------------------------------
# MultiSelectPayload (MULTI discriminated union)
# ---------------------------------------------------------------------------

class TestMultiSelectPayload:
    def _make(self, **kwargs):
        defaults = dict(
            question_type="multi",
            question_text="Which of the following are programming languages?",
            options=[OptionCreate(text=f"Lang{i}") for i in range(4)],
            correct_answers=[1, 3],
        )
        defaults.update(kwargs)
        return MultiSelectPayload(**defaults)

    def test_valid_payload(self):
        p = self._make()
        assert p.question_type == "multi"
        assert p.correct_answers == [1, 3]

    def test_empty_correct_answers_raises(self):
        with pytest.raises(ValidationError):
            self._make(correct_answers=[])

    def test_out_of_range_answer_raises(self):
        with pytest.raises(ValidationError, match="out of range"):
            self._make(
                options=[OptionCreate(text=f"O{i}") for i in range(3)],
                correct_answers=[1, 99],
            )

    def test_duplicate_correct_answers_raises(self):
        with pytest.raises(ValidationError, match="duplicates"):
            self._make(correct_answers=[1, 1])

    def test_all_options_correct_raises(self):
        with pytest.raises(ValidationError, match="cannot mark all options correct"):
            self._make(
                options=[OptionCreate(text=f"O{i}") for i in range(2)],
                correct_answers=[1, 2],
            )

    def test_too_few_options_raises(self):
        with pytest.raises(ValidationError):
            self._make(options=[OptionCreate(text="One")])
