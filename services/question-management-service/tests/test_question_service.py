import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.question import OptionCreate, QuestionType
from src.schemas.question import QuestionCreate, QuestionUpdate
from src.services.question_service import QuestionService
from src.v1.routes import question_routes


def mcq_create(**overrides):
    payload = {
        "type": QuestionType.MCQ,
        "question_text": "Which language is commonly used with FastAPI?",
        "options": [{"text": "Python"}, {"text": "COBOL"}],
        "correct_answers": [1],
        "difficulty": "easy",
        "skills": ["Python"],
        "tags": ["backend"],
    }
    payload.update(overrides)
    return QuestionCreate(**payload)


def question_doc(question_type=QuestionType.MCQ):
    options = (
        [
            {"option_id": 1, "text": "Python"},
            {"option_id": 2, "text": "COBOL"},
        ]
        if question_type in (QuestionType.MCQ, QuestionType.MULTI)
        else None
    )
    return SimpleNamespace(
        type=question_type,
        question_text="Which language is commonly used with FastAPI?",
        options=options,
        correct_answers=[1] if question_type == QuestionType.MCQ else None,
        sample_answer="A sufficiently detailed text answer."
        if question_type == QuestionType.TEXT
        else None,
        difficulty="medium",
        skills=["Python"],
        tags=["backend"],
        model_dump=lambda **kwargs: {
            "type": question_type.value,
            "question_text": "Which language is commonly used with FastAPI?",
            "options": options,
            "correct_answers": [1] if question_type == QuestionType.MCQ else None,
            "sample_answer": None,
            "answer_explanation": None,
            "difficulty": "medium",
            "skills": ["Python"],
            "tags": ["backend"],
        },
    )


def response_doc(doc_id="qid"):
    return SimpleNamespace(
        model_dump=lambda **kwargs: {
            "_id": doc_id,
            "type": "mcq",
            "question_text": "Which language is commonly used with FastAPI?",
            "options": [{"option_id": 1, "text": "Python"}],
            "correct_answers": [1],
            "sample_answer": None,
            "answer_explanation": None,
            "difficulty": "easy",
            "skills": ["Python"],
            "tags": ["backend"],
            "created_at": "2026-06-05T00:00:00",
            "updated_at": "2026-06-05T00:00:00",
        }
    )


def test_convert_options_assigns_one_indexed_ids_and_handles_none():
    options = [OptionCreate(text=" A "), OptionCreate(text="B")]

    stored = QuestionService.convert_options_to_stored_format(options)

    assert QuestionService.convert_options_to_stored_format(None) is None
    assert [(opt.option_id, opt.text) for opt in stored] == [(1, "A"), (2, "B")]


@pytest.mark.asyncio
async def test_create_question_converts_options_before_repository_create():
    fake_question = SimpleNamespace()
    with (
        patch("src.services.question_service.Question", return_value=fake_question),
        patch(
            "src.services.question_service.QuestionRepository.create",
            new=AsyncMock(return_value="abc123"),
        ) as create,
    ):
        result = await QuestionService.create_question(mcq_create())

    assert result == "abc123"
    saved_question = create.await_args.args[0]
    assert saved_question is fake_question


@pytest.mark.asyncio
async def test_create_question_wraps_validation_and_unexpected_errors():
    with (
        patch("src.services.question_service.Question", return_value=SimpleNamespace()),
        patch(
            "src.services.question_service.QuestionRepository.create",
            new=AsyncMock(side_effect=ValueError("bad question")),
        ),
    ):
        with pytest.raises(HTTPException) as bad_request:
            await QuestionService.create_question(mcq_create())
    assert bad_request.value.status_code == 400

    with (
        patch("src.services.question_service.Question", return_value=SimpleNamespace()),
        patch(
            "src.services.question_service.QuestionRepository.create",
            new=AsyncMock(side_effect=RuntimeError("database down")),
        ),
    ):
        with pytest.raises(HTTPException) as server_error:
            await QuestionService.create_question(mcq_create())
    assert server_error.value.status_code == 500


@pytest.mark.asyncio
async def test_update_question_returns_false_when_missing_and_updates_when_valid():
    with patch(
        "src.services.question_service.QuestionRepository.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        assert await QuestionService.update_question("missing", QuestionUpdate()) is False

    with (
        patch(
            "src.services.question_service.QuestionRepository.get_by_id",
            new=AsyncMock(return_value=question_doc()),
        ),
        patch(
            "src.services.question_service.QuestionRepository.update",
            new=AsyncMock(return_value=True),
        ) as update,
    ):
        result = await QuestionService.update_question(
            "qid",
            QuestionUpdate(
                options=[{"text": "Python"}, {"text": "Java"}],
                correct_answers=[2],
            ),
        )

    assert result is True
    update_data = update.await_args.args[1]
    assert update_data["options"][0]["option_id"] == 1
    assert update_data["correct_answers"] == [2]
    assert "updated_at" in update_data


@pytest.mark.parametrize(
    ("question_type", "existing", "update", "message"),
    [
        (
            QuestionType.MCQ.value,
            {"options": [{"option_id": 1, "text": "A"}], "correct_answers": [1]},
            {"correct_answers": [1, 2]},
            "exactly one",
        ),
        (
            QuestionType.MULTI.value,
            {
                "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
                "correct_answers": [1],
            },
            {"correct_answers": [1, 1]},
            "duplicates",
        ),
        (
            QuestionType.TRUE_FALSE.value,
            {"correct_answers": [True]},
            {"options": [{"option_id": 1, "text": "True"}]},
            "should not have options",
        ),
        (
            QuestionType.TEXT.value,
            {"sample_answer": "A long enough answer"},
            {"sample_answer": "short"},
            "at least 10",
        ),
    ],
)
def test_validate_update_for_type_rejects_invalid_payloads(
    question_type,
    existing,
    update,
    message,
):
    with pytest.raises(ValueError) as exc:
        QuestionService._validate_update_for_type(question_type, existing, update)

    assert message in str(exc.value)


@pytest.mark.parametrize(
    ("question_type", "existing", "update", "message"),
    [
        (
            QuestionType.MCQ.value,
            {"options": [{"option_id": 1, "text": "A"}], "correct_answers": [1]},
            {"options": [{"option_id": 1, "text": "Only one"}]},
            "at least 2",
        ),
        (
            QuestionType.MCQ.value,
            {"options": [{"option_id": 1, "text": "A"}], "correct_answers": [1]},
            {"correct_answers": ["1"]},
            "must be an integer",
        ),
        (
            QuestionType.MCQ.value,
            {"options": [{"option_id": 1, "text": "A"}], "correct_answers": [1]},
            {"correct_answers": [2]},
            "not a valid option_id",
        ),
        (
            QuestionType.MULTI.value,
            {"options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}]},
            {"correct_answers": []},
            "at least one",
        ),
        (
            QuestionType.MULTI.value,
            {"options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}]},
            {"correct_answers": ["1"]},
            "list of integers",
        ),
        (
            QuestionType.MULTI.value,
            {"options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}]},
            {"correct_answers": [3]},
            "invalid option_id",
        ),
        (
            QuestionType.MULTI.value,
            {"options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}]},
            {"correct_answers": [1, 2]},
            "cannot have all options",
        ),
        (
            QuestionType.TRUE_FALSE.value,
            {"correct_answers": [True]},
            {"correct_answers": [True, False]},
            "exactly one",
        ),
        (
            QuestionType.TRUE_FALSE.value,
            {"correct_answers": [True]},
            {"correct_answers": ["true"]},
            "boolean value",
        ),
        (
            QuestionType.TEXT.value,
            {"sample_answer": "A long enough sample answer."},
            {"correct_answers": [1]},
            "should not have correct_answers",
        ),
        (
            QuestionType.TEXT.value,
            {"sample_answer": "A long enough sample answer."},
            {"sample_answer": "   "},
            "non-empty",
        ),
    ],
)
def test_validate_update_for_type_rejects_additional_edge_cases(
    question_type,
    existing,
    update,
    message,
):
    with pytest.raises(ValueError) as exc:
        QuestionService._validate_update_for_type(question_type, existing, update)

    assert message in str(exc.value)


@pytest.mark.asyncio
async def test_update_question_converts_validation_errors_to_http_400():
    with patch(
        "src.services.question_service.QuestionRepository.get_by_id",
        new=AsyncMock(return_value=question_doc(QuestionType.TRUE_FALSE)),
    ):
        with pytest.raises(HTTPException) as exc:
            await QuestionService.update_question(
                "qid",
                QuestionUpdate(options=[{"text": "True"}, {"text": "False"}]),
            )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_simple_passthrough_queries_delegate_to_repository():
    with (
        patch(
            "src.services.question_service.QuestionRepository.get_all",
            new=AsyncMock(return_value=["all"]),
        ),
        patch(
            "src.services.question_service.QuestionRepository.get_by_id",
            new=AsyncMock(return_value="one"),
        ),
        patch(
            "src.services.question_service.QuestionRepository.delete",
            new=AsyncMock(return_value=True),
        ),
    ):
        assert await QuestionService.get_all_questions() == ["all"]
        assert await QuestionService.get_question_by_id("qid") == "one"
        assert await QuestionService.delete_question("qid") is True


@pytest.mark.asyncio
async def test_find_helpers_validate_input_and_delegate_to_repository():
    with patch(
        "src.services.question_service.QuestionRepository.find_by_type",
        new=AsyncMock(return_value=["typed"]),
    ) as find_by_type:
        assert await QuestionService.find_by_type("mcq", 5) == ["typed"]
        find_by_type.assert_awaited_once_with("mcq", 5)

    with pytest.raises(HTTPException):
        await QuestionService.find_by_type("essay")

    with patch(
        "src.services.question_service.QuestionRepository.find_by_skill",
        new=AsyncMock(return_value=["skilled"]),
    ) as find_by_skill:
        assert await QuestionService.find_by_skill(" Python ", 2) == ["skilled"]
        find_by_skill.assert_awaited_once_with("Python", 2)

    with pytest.raises(HTTPException):
        await QuestionService.find_by_skill("   ")

    with patch(
        "src.services.question_service.QuestionRepository.find_by_difficulty",
        new=AsyncMock(return_value=["hard"]),
    ):
        assert await QuestionService.find_by_difficulty("hard") == ["hard"]

    with pytest.raises(HTTPException):
        await QuestionService.find_by_difficulty("expert")

    with patch(
        "src.services.question_service.QuestionRepository.find_by_tags",
        new=AsyncMock(return_value=["tagged"]),
    ) as find_by_tags:
        assert await QuestionService.find_by_tags([" api ", "", "fastapi"]) == ["tagged"]
        find_by_tags.assert_awaited_once_with(["api", "fastapi"], 100)

    with pytest.raises(HTTPException):
        await QuestionService.find_by_tags([])

    with pytest.raises(HTTPException):
        await QuestionService.find_by_tags(["  "])


def test_question_create_schema_rejects_type_specific_invalid_payloads():
    with pytest.raises(ValidationError):
        mcq_create(correct_answers=[1, 2])

    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MULTI,
            question_text="Choose the valid backend languages.",
            options=[{"text": "Python"}, {"text": "Java"}],
            correct_answers=[1, 2],
        )

    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TRUE_FALSE,
            question_text="FastAPI is a Python framework.",
            options=[{"text": "True"}, {"text": "False"}],
            correct_answers=[True],
        )

    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.TEXT,
            question_text="Explain dependency injection in FastAPI.",
            sample_answer="short",
        )


def test_question_update_schema_sanitizes_lists_and_checks_answer_positions():
    update = QuestionUpdate(skills=[" Python ", "FastAPI"], tags=[" api ", "backend"])

    assert update.skills == ["Python", "FastAPI"]
    assert update.tags == ["api", "backend"]

    with pytest.raises(ValidationError):
        QuestionUpdate(skills=["Python", "Python"])

    with pytest.raises(ValidationError):
        QuestionUpdate(
            options=[{"text": "A"}, {"text": "B"}],
            correct_answers=[3],
        )


@pytest.mark.asyncio
async def test_question_routes_delegate_successfully():
    doc = response_doc()
    with patch.object(
        question_routes.QuestionService,
        "create_question",
        new=AsyncMock(return_value="qid"),
    ):
        created = await question_routes.create_question(mcq_create())
    assert created == {"message": "Question created successfully", "id": "qid"}

    with patch.object(
        question_routes.QuestionService,
        "get_all_questions",
        new=AsyncMock(return_value=[doc]),
    ):
        listed = await question_routes.get_all_questions()
    assert listed[0].id == "qid"

    with patch.object(
        question_routes.QuestionService,
        "get_question_by_id",
        new=AsyncMock(return_value=doc),
    ):
        found = await question_routes.get_question_by_id("qid")
    assert found.id == "qid"

    with patch.object(
        question_routes.QuestionService,
        "update_question",
        new=AsyncMock(return_value=True),
    ):
        updated = await question_routes.update_question("qid", QuestionUpdate())
    assert updated["id"] == "qid"

    with patch.object(
        question_routes.QuestionService,
        "delete_question",
        new=AsyncMock(return_value=True),
    ):
        deleted = await question_routes.delete_question("qid")
    assert deleted["id"] == "qid"


@pytest.mark.asyncio
async def test_question_routes_raise_expected_not_found_and_server_errors():
    with patch.object(
        question_routes.QuestionService,
        "get_question_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as not_found:
            await question_routes.get_question_by_id("missing")
    assert not_found.value.status_code == 404

    with patch.object(
        question_routes.QuestionService,
        "get_all_questions",
        new=AsyncMock(side_effect=RuntimeError("database down")),
    ):
        with pytest.raises(HTTPException) as server_error:
            await question_routes.get_all_questions()
    assert server_error.value.status_code == 500

    with patch.object(
        question_routes.QuestionService,
        "update_question",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as missing_update:
            await question_routes.update_question("missing", QuestionUpdate())
    assert missing_update.value.status_code == 404

    with patch.object(
        question_routes.QuestionService,
        "delete_question",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as missing_delete:
            await question_routes.delete_question("missing")
    assert missing_delete.value.status_code == 404


@pytest.mark.asyncio
async def test_question_filter_routes_delegate_to_service():
    docs = [response_doc()]
    with patch.object(
        question_routes.QuestionService,
        "find_by_type",
        new=AsyncMock(return_value=docs),
    ):
        assert len(await question_routes.get_questions_by_type("mcq", 5)) == 1

    with patch.object(
        question_routes.QuestionService,
        "find_by_skill",
        new=AsyncMock(return_value=docs),
    ):
        assert len(await question_routes.get_questions_by_skill("Python", 5)) == 1

    with patch.object(
        question_routes.QuestionService,
        "find_by_difficulty",
        new=AsyncMock(return_value=docs),
    ):
        assert len(await question_routes.get_questions_by_difficulty("easy", 5)) == 1

    with patch.object(
        question_routes.QuestionService,
        "find_by_tags",
        new=AsyncMock(return_value=docs),
    ):
        assert len(await question_routes.get_questions_by_tags(["api"], 5)) == 1

    with patch.object(
        question_routes.QuestionService,
        "filter_questions",
        new=AsyncMock(return_value=docs),
    ):
        filtered = await question_routes.filter_questions(
            type="mcq",
            skill="Python",
            difficulty="easy",
            tags=["api"],
            limit=5,
        )
    assert len(filtered) == 1


@pytest.mark.asyncio
async def test_filter_questions_rejects_missing_and_invalid_filters():
    with pytest.raises(HTTPException) as missing_filters:
        await QuestionService.filter_questions()
    assert missing_filters.value.status_code == 400

    with pytest.raises(HTTPException) as invalid_type:
        await QuestionService.filter_questions(question_type="essay")
    assert invalid_type.value.status_code == 400

    with pytest.raises(HTTPException) as invalid_difficulty:
        await QuestionService.filter_questions(difficulty="expert")
    assert invalid_difficulty.value.status_code == 400


@pytest.mark.asyncio
async def test_filter_questions_executes_single_type_condition():
    class FakeField:
        def __eq__(self, value):
            return ("eq", value)

    class FakeQuery:
        def __init__(self, condition):
            self.condition = condition
            self.limit_value = None

        def limit(self, value):
            self.limit_value = value
            return self

        async def to_list(self):
            return [self.condition, self.limit_value]

    class FakeQuestion:
        type = FakeField()

        @staticmethod
        def find(condition):
            return FakeQuery(condition)

    with patch("src.services.question_service.Question", FakeQuestion):
        result = await QuestionService.filter_questions(question_type="mcq", limit=7)

    assert result == [("eq", "mcq"), 7]
