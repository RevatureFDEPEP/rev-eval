"""QuestionPublic must never carry the answer key.

The ``/questions/sample`` endpoint serializes through QuestionPublic so a
question body can seed a quiz session (and reach the test-taker as
``first_question``) without leaking how it is graded.
"""
from datetime import datetime

from src.schemas.question import QuestionPublic, QuestionResponse

_ANSWER_KEY_FIELDS = {"correct_answers", "sample_answer", "answer_explanation"}

_FULL_DOC = {
    "_id": "abc123",
    "type": "mcq",
    "question_text": "Which is a Python keyword?",
    "options": [{"option_id": 1, "text": "def"}, {"option_id": 2, "text": "func"}],
    "correct_answers": [1],
    "sample_answer": None,
    "answer_explanation": "def declares a function.",
    "difficulty": "easy",
    "skills": ["python"],
    "tags": ["syntax"],
    "image_object_key": None,
    "created_at": datetime(2026, 6, 1),
    "updated_at": datetime(2026, 6, 1),
}


def test_public_schema_omits_answer_key_fields():
    assert _ANSWER_KEY_FIELDS.isdisjoint(QuestionPublic.model_fields)
    # The full response schema, by contrast, still exposes them (trainer-gated).
    assert _ANSWER_KEY_FIELDS.issubset(QuestionResponse.model_fields)


def test_public_dump_drops_answer_key_even_from_full_doc():
    public = QuestionPublic(**_FULL_DOC)
    dumped = public.model_dump(by_alias=True)
    for field in _ANSWER_KEY_FIELDS:
        assert field not in dumped
    # Non-sensitive fields survive.
    assert dumped["question_text"] == _FULL_DOC["question_text"]
    assert dumped["_id"] == "abc123"
