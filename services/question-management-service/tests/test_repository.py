import pytest
from src.models.question import Option, Question, QuestionType
from src.repositories.question_repository import QuestionRepository


def _mcq(**overrides) -> Question:
    defaults = dict(
        type=QuestionType.MCQ,
        question_text="What is Java primarily used for in enterprise apps?",
        options=[
            Option(option_id=1, text="Backend development"),
            Option(option_id=2, text="Painting pictures"),
            Option(option_id=3, text="Hardware design"),
        ],
        correct_answers=[1],
        skills=["Java"],
        tags=["java", "enterprise"],
        difficulty="easy",
    )
    defaults.update(overrides)
    return Question(**defaults)


class TestQuestionRepositoryCreate:
    async def test_create_returns_string_id(self, question_db):
        qid = await QuestionRepository.create(_mcq())
        assert isinstance(qid, str)
        assert len(qid) > 0

    async def test_create_different_questions_get_different_ids(self, question_db):
        id1 = await QuestionRepository.create(_mcq(question_text="First question text here?"))
        id2 = await QuestionRepository.create(_mcq(question_text="Second question text here?"))
        assert id1 != id2


class TestQuestionRepositoryRead:
    async def test_get_by_id_found(self, question_db):
        qid = await QuestionRepository.create(_mcq())
        found = await QuestionRepository.get_by_id(qid)
        assert found is not None
        assert str(found.id) == qid

    async def test_get_by_id_not_found_returns_none(self, question_db):
        result = await QuestionRepository.get_by_id("000000000000000000000001")
        assert result is None

    async def test_get_by_invalid_id_returns_none(self, question_db):
        result = await QuestionRepository.get_by_id("not-a-valid-objectid")
        assert result is None

    async def test_get_all_empty_returns_empty_list(self, question_db):
        questions = await QuestionRepository.get_all()
        assert questions == []

    async def test_get_all_returns_created_questions(self, question_db):
        await QuestionRepository.create(_mcq(question_text="Question one text here?"))
        await QuestionRepository.create(_mcq(question_text="Question two text here?"))
        questions = await QuestionRepository.get_all()
        assert len(questions) == 2

    async def test_get_all_pagination_limit(self, question_db):
        for i in range(5):
            await QuestionRepository.create(_mcq(question_text=f"Question number {i} here?"))
        first_page = await QuestionRepository.get_all(limit=3, skip=0)
        assert len(first_page) == 3

    async def test_get_all_pagination_skip(self, question_db):
        for i in range(5):
            await QuestionRepository.create(_mcq(question_text=f"Question page {i} here?"))
        second_page = await QuestionRepository.get_all(limit=3, skip=3)
        assert len(second_page) == 2


class TestQuestionRepositoryUpdate:
    async def test_update_question_text(self, question_db):
        qid = await QuestionRepository.create(_mcq())
        success = await QuestionRepository.update(qid, {"question_text": "Updated question text here"})
        assert success is True
        updated = await QuestionRepository.get_by_id(qid)
        assert updated.question_text == "Updated question text here"

    async def test_update_difficulty(self, question_db):
        qid = await QuestionRepository.create(_mcq(difficulty="easy"))
        await QuestionRepository.update(qid, {"difficulty": "hard"})
        updated = await QuestionRepository.get_by_id(qid)
        assert updated.difficulty == "hard"

    async def test_update_nonexistent_returns_false(self, question_db):
        result = await QuestionRepository.update("000000000000000000000001", {"question_text": "nope"})
        assert result is False


class TestQuestionRepositoryDelete:
    async def test_delete_existing_returns_true(self, question_db):
        qid = await QuestionRepository.create(_mcq())
        result = await QuestionRepository.delete(qid)
        assert result is True

    async def test_deleted_question_not_found(self, question_db):
        qid = await QuestionRepository.create(_mcq())
        await QuestionRepository.delete(qid)
        assert await QuestionRepository.get_by_id(qid) is None

    async def test_delete_nonexistent_returns_false(self, question_db):
        result = await QuestionRepository.delete("000000000000000000000001")
        assert result is False


class TestQuestionRepositoryCount:
    async def test_count_zero_initially(self, question_db):
        assert await QuestionRepository.count() == 0

    async def test_count_increments_on_create(self, question_db):
        await QuestionRepository.create(_mcq(question_text="Count test one here?"))
        await QuestionRepository.create(_mcq(question_text="Count test two here?"))
        assert await QuestionRepository.count() == 2


class TestQuestionRepositoryFilters:
    async def test_find_by_type(self, question_db):
        await QuestionRepository.create(_mcq())
        await QuestionRepository.create(_mcq())
        results = await QuestionRepository.find_by_type("mcq")
        assert len(results) == 2

    async def test_find_by_type_no_match(self, question_db):
        await QuestionRepository.create(_mcq())
        results = await QuestionRepository.find_by_type("text")
        assert len(results) == 0

    async def test_find_by_skill(self, question_db):
        await QuestionRepository.create(_mcq(skills=["Python"]))
        await QuestionRepository.create(_mcq(skills=["Java"]))
        results = await QuestionRepository.find_by_skill("Python")
        assert len(results) == 1

    async def test_find_by_difficulty_easy(self, question_db):
        await QuestionRepository.create(_mcq(difficulty="easy"))
        await QuestionRepository.create(_mcq(difficulty="hard"))
        easy = await QuestionRepository.find_by_difficulty("easy")
        assert len(easy) == 1

    @pytest.mark.parametrize("tags,search,expected", [
        (["java", "oop"], "java", 1),
        (["python", "django"], "flask", 0),
        (["spring", "java"], "java", 1),
    ])
    async def test_find_by_tags(self, question_db, tags, search, expected):
        await QuestionRepository.create(_mcq(tags=tags))
        results = await QuestionRepository.find_by_tags([search])
        assert len(results) == expected
