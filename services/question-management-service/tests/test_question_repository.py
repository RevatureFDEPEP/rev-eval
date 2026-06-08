"""Repository-level tests for QuestionRepository against an in-memory Mongo.

These run real Beanie query paths via the `beanie_db` fixture (conftest.py),
which is backed by mongomock-motor — no MongoDB required. They cover CRUD,
pagination, count, and the find_by_* query helpers, plus type-aware
QuestionCreate validation.
"""
import pytest
from src.models.question import Option, Question, QuestionType
from src.repositories.question_repository import QuestionRepository
from src.schemas.question import QuestionCreate


def _mcq(question_text="Which language runs in a browser natively?") -> Question:
    return Question(
        type=QuestionType.MCQ,
        question_text=question_text,
        options=[Option(option_id=1, text="Python"), Option(option_id=2, text="JavaScript")],
        correct_answers=[2],
        difficulty="easy",
        skills=["JavaScript"],
        tags=["web"],
    )


def _text(question_text="Explain dependency injection in your own words.") -> Question:
    return Question(
        type=QuestionType.TEXT,
        question_text=question_text,
        sample_answer="Supplying a component's collaborators from outside.",
        difficulty="hard",
        skills=["Design"],
        tags=["patterns"],
    )


async def test_create_returns_id_and_get_by_id_roundtrips(beanie_db):
    qid = await QuestionRepository.create(_mcq())
    assert isinstance(qid, str) and qid

    fetched = await QuestionRepository.get_by_id(qid)
    assert fetched is not None
    assert fetched.type == QuestionType.MCQ
    assert fetched.question_text.startswith("Which language")


async def test_get_by_id_invalid_returns_none(beanie_db):
    assert await QuestionRepository.get_by_id("not-an-objectid") is None


async def test_get_all_paginates(beanie_db):
    for i in range(3):
        await QuestionRepository.create(_text(f"Question number {i} explain something here?"))

    page = await QuestionRepository.get_all(limit=2, skip=0)
    assert len(page) == 2
    page2 = await QuestionRepository.get_all(limit=2, skip=2)
    assert len(page2) == 1


async def test_update_modifies_fields(beanie_db):
    qid = await QuestionRepository.create(_text())
    ok = await QuestionRepository.update(qid, {"difficulty": "medium"})
    assert ok is True
    assert (await QuestionRepository.get_by_id(qid)).difficulty == "medium"


async def test_update_missing_returns_false(beanie_db):
    from beanie import PydanticObjectId

    missing = str(PydanticObjectId())
    assert await QuestionRepository.update(missing, {"difficulty": "easy"}) is False


async def test_delete_removes_document(beanie_db):
    qid = await QuestionRepository.create(_mcq())
    assert await QuestionRepository.delete(qid) is True
    assert await QuestionRepository.get_by_id(qid) is None
    # Second delete on the now-missing doc is False, not an error.
    assert await QuestionRepository.delete(qid) is False


async def test_count_reflects_inserts(beanie_db):
    assert await QuestionRepository.count() == 0
    await QuestionRepository.create(_mcq())
    await QuestionRepository.create(_text())
    assert await QuestionRepository.count() == 2


async def test_find_by_type(beanie_db):
    await QuestionRepository.create(_mcq())
    await QuestionRepository.create(_text())
    mcqs = await QuestionRepository.find_by_type("mcq")
    assert len(mcqs) == 1
    assert mcqs[0].type == QuestionType.MCQ


async def test_find_by_skill_and_difficulty_and_tags(beanie_db):
    await QuestionRepository.create(_mcq())  # skill JavaScript, easy, tag web
    await QuestionRepository.create(_text())  # skill Design, hard, tag patterns

    assert len(await QuestionRepository.find_by_skill("JavaScript")) == 1
    assert len(await QuestionRepository.find_by_difficulty("hard")) == 1
    assert len(await QuestionRepository.find_by_tags(["web", "patterns"])) == 2


# --- type-aware QuestionCreate validation (no DB) ---


def test_question_create_mcq_valid():
    q = QuestionCreate(
        type=QuestionType.MCQ,
        question_text="Which is a Python web framework here?",
        options=[{"text": "FastAPI"}, {"text": "Express"}],
        correct_answers=[1],
    )
    assert q.type == QuestionType.MCQ


@pytest.mark.parametrize(
    "kwargs",
    [
        # MCQ with no options
        dict(type=QuestionType.MCQ, question_text="A question without any options here",
             correct_answers=[1]),
        # MCQ with more than one correct answer
        dict(type=QuestionType.MCQ, question_text="A question with two corrects here",
             options=[{"text": "A"}, {"text": "B"}], correct_answers=[1, 2]),
        # TEXT missing sample_answer
        dict(type=QuestionType.TEXT, question_text="A text question lacking a sample"),
        # TRUE_FALSE with non-boolean correct answer
        dict(type=QuestionType.TRUE_FALSE, question_text="Is this a boolean question here",
             correct_answers=[1]),
    ],
)
def test_question_create_invalid_by_type(kwargs):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        QuestionCreate(**kwargs)
