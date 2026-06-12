"""Regression tests: participant-facing question views must not leak answer keys."""
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schemas.question import QuestionPublic, QuestionResponse
from src.v1.routes import question_routes

_SENSITIVE = ("correct_answers", "answer_explanation", "sample_answer")


def _full_question_doc():
    """A Beanie-document-like stand-in exposing model_dump(by_alias, mode)."""
    data = {
        "_id": "abc123",
        "type": "mcq",
        "question_text": "Pick the right option here please.",
        "options": [{"text": "a"}, {"text": "b"}],
        "correct_answers": [2],
        "answer_explanation": "b is correct",
        "sample_answer": None,
        "difficulty": "easy",
        "skills": ["python"],
        "tags": ["loops"],
        "created_at": datetime(2024, 1, 1).isoformat(),
        "updated_at": datetime(2024, 1, 1).isoformat(),
    }
    return SimpleNamespace(model_dump=lambda by_alias, mode: dict(data))


def test_public_schema_drops_all_answer_key_fields():
    full = _full_question_doc().model_dump(by_alias=True, mode="json")
    public = QuestionPublic(**full).model_dump(by_alias=True, mode="json")
    for field in _SENSITIVE:
        assert field not in public
    assert public["question_text"]


def test_full_schema_retains_answer_keys_for_trainers():
    full = _full_question_doc().model_dump(by_alias=True, mode="json")
    serialized = QuestionResponse(**full).model_dump(by_alias=True, mode="json")
    assert serialized["correct_answers"] == [2]


def test_serialize_strips_for_participant_role():
    doc = _full_question_doc()
    out = question_routes._serialize(doc, privileged=question_routes._is_privileged("PARTICIPANT"))
    for field in _SENSITIVE:
        assert field not in out


def test_serialize_strips_for_missing_role():
    doc = _full_question_doc()
    out = question_routes._serialize(doc, privileged=question_routes._is_privileged(None))
    assert "correct_answers" not in out


def test_serialize_keeps_keys_for_trainer_and_admin():
    doc = _full_question_doc()
    for role in ("TRAINER", "ADMIN", "trainer", "admin"):
        out = question_routes._serialize(doc, privileged=question_routes._is_privileged(role))
        assert out["correct_answers"] == [2]
