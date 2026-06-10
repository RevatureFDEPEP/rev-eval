import pytest
from pydantic import ValidationError
from src.schemas.question import QuestionCreate, QuestionUpdate

# ── Shared valid payloads ──────────────────────────────────────────────────────

_MCQ_OPTIONS = [
    {"text": "Option A"},
    {"text": "Option B"},
    {"text": "Option C"},
]

VALID_MCQ = dict(
    type="mcq",
    question_text="What is the capital of France?",
    options=_MCQ_OPTIONS,
    correct_answers=[1],
    skills=["Geography"],
)

VALID_MULTI = dict(
    type="multi",
    question_text="Which of the following are Python data types?",
    options=[{"text": "int"}, {"text": "str"}, {"text": "list"}, {"text": "java"}],
    correct_answers=[1, 2, 3],
    skills=["Python"],
)

VALID_TF = dict(
    type="true_false",
    question_text="Python is a statically typed language.",
    correct_answers=[False],
    skills=["Python"],
)

VALID_TEXT = dict(
    type="text",
    question_text="Explain the difference between a list and a tuple in Python.",
    sample_answer="Lists are mutable while tuples are immutable data structures.",
    skills=["Python"],
)


# ── MCQ ───────────────────────────────────────────────────────────────────────

class TestMCQSchema:
    def test_valid_mcq(self):
        q = QuestionCreate(**VALID_MCQ)
        assert q.correct_answers == [1]

    @pytest.mark.parametrize("num_options", [2, 3, 4, 5, 10])
    def test_accepts_2_to_10_options(self, num_options):
        options = [{"text": f"Option {i}"} for i in range(num_options)]
        q = QuestionCreate(
            type="mcq",
            question_text="A valid question text here?",
            options=options,
            correct_answers=[1],
            skills=["Test"],
        )
        assert len(q.options) == num_options

    def test_rejects_single_option(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "options": [{"text": "Only one"}]})

    def test_rejects_more_than_10_options(self):
        options = [{"text": f"Option {i}"} for i in range(11)]
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "options": options, "correct_answers": [1]})

    def test_rejects_missing_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "correct_answers": None})

    def test_rejects_multiple_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "correct_answers": [1, 2]})

    def test_correct_answer_must_not_be_string(self):
        # bool is a subclass of int in Python so [True] passes; strings must not
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "correct_answers": ["first"]})

    def test_correct_answer_out_of_range(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "correct_answers": [99]})

    def test_rejects_duplicate_option_text(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{
                **VALID_MCQ,
                "options": [{"text": "Dup"}, {"text": "Dup"}],
                "correct_answers": [1],
            })


# ── MULTI ─────────────────────────────────────────────────────────────────────

class TestMULTISchema:
    def test_valid_multi(self):
        q = QuestionCreate(**VALID_MULTI)
        assert len(q.correct_answers) == 3

    def test_rejects_empty_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MULTI, "correct_answers": []})

    def test_rejects_boolean_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MULTI, "correct_answers": [True, False]})

    def test_rejects_all_options_correct(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MULTI, "correct_answers": [1, 2, 3, 4]})

    def test_rejects_duplicate_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MULTI, "correct_answers": [1, 1, 2]})

    def test_correct_answer_out_of_range(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MULTI, "correct_answers": [1, 99]})


# ── TRUE/FALSE ────────────────────────────────────────────────────────────────

class TestTrueFalseSchema:
    @pytest.mark.parametrize("answer", [True, False])
    def test_accepts_both_boolean_answers(self, answer):
        q = QuestionCreate(**{**VALID_TF, "correct_answers": [answer]})
        assert q.correct_answers[0] == answer

    def test_rejects_options_field(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TF, "options": [{"text": "A"}, {"text": "B"}]})

    def test_rejects_integer_answer(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TF, "correct_answers": [1]})

    def test_rejects_multiple_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TF, "correct_answers": [True, False]})

    def test_rejects_missing_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TF, "correct_answers": None})


# ── TEXT ──────────────────────────────────────────────────────────────────────

class TestTextSchema:
    def test_valid_text_question(self):
        q = QuestionCreate(**VALID_TEXT)
        assert q.sample_answer is not None

    def test_rejects_missing_sample_answer(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TEXT, "sample_answer": None})

    def test_rejects_short_sample_answer(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TEXT, "sample_answer": "Short"})

    def test_rejects_options(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TEXT, "options": [{"text": "A"}, {"text": "B"}]})

    def test_rejects_correct_answers(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_TEXT, "correct_answers": ["yes"]})


# ── Shared field validation ────────────────────────────────────────────────────

class TestSharedValidation:
    @pytest.mark.parametrize("q_text", ["Short", "tiny", "         "])
    def test_question_text_too_short_rejected(self, q_text):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "question_text": q_text})

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_valid_difficulty_values(self, difficulty):
        q = QuestionCreate(**{**VALID_MCQ, "difficulty": difficulty})
        assert q.difficulty == difficulty

    def test_invalid_difficulty_rejected(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "difficulty": "extreme"})

    def test_duplicate_skills_rejected(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "skills": ["Python", "Python"]})

    def test_exceeding_20_skills_rejected(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "skills": [f"Skill{i}" for i in range(21)]})

    def test_duplicate_tags_rejected(self):
        with pytest.raises(ValidationError):
            QuestionCreate(**{**VALID_MCQ, "tags": ["java", "java"]})

    def test_skills_whitespace_stripped(self):
        q = QuestionCreate(**{**VALID_MCQ, "skills": ["  Python  ", "  Java  "]})
        assert "Python" in q.skills
        assert "Java" in q.skills


# ── QuestionUpdate ────────────────────────────────────────────────────────────

class TestQuestionUpdateSchema:
    def test_all_fields_optional(self):
        update = QuestionUpdate()
        assert update.question_text is None
        assert update.options is None
        assert update.correct_answers is None
        assert update.difficulty is None

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_valid_difficulty(self, difficulty):
        update = QuestionUpdate(difficulty=difficulty)
        assert update.difficulty == difficulty

    def test_invalid_difficulty_rejected(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(difficulty="extreme")

    def test_consistent_options_and_correct_answers(self):
        update = QuestionUpdate(
            options=[{"text": "A"}, {"text": "B"}, {"text": "C"}],
            correct_answers=[1],
        )
        assert len(update.options) == 3

    def test_out_of_range_correct_answer_rejected(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(
                options=[{"text": "A"}, {"text": "B"}],
                correct_answers=[5],
            )

    def test_duplicate_skills_rejected(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(skills=["Java", "Java"])

    def test_duplicate_tags_rejected(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(tags=["oop", "oop"])
