"""Service-layer coverage for QuestionService (repository + Beanie mocked).

Hermetic: repository calls are patched with AsyncMocks. Tests assert the
service's *real* behaviour — option-id auto-generation, the type-aware update
guard (_validate_update_for_type), argument cleaning, and error mapping — not
just a mocked return value.

The Beanie query path in filter_questions (Question.type == ..., Question.find)
needs an initialised ODM / live Mongo, so only its validation branches are
unit-tested here; the query execution is left to integration coverage rather
than faked with brittle field mocks.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.models.question import OptionCreate
from src.schemas.question import QuestionCreate, QuestionUpdate
from src.services.question_service import QuestionService

SVC = "src.services.question_service.QuestionRepository"
TEXT = "A sufficiently long question text"


def _existing(type_="mcq", **overrides):
    """A stand-in for a fetched Question document (avoids Beanie init).

    Exposes .type and .model_dump() — the only things update_question reads."""
    doc = MagicMock()
    doc.type = type_
    dump = {
        "type": type_,
        "options": [{"option_id": 1}, {"option_id": 2}],
        "correct_answers": [1],
    }
    dump.update(overrides)
    doc.model_dump.return_value = dump
    return doc


# ----- convert_options_to_stored_format ------------------------------------


def test_convert_options_none_returns_none():
    assert QuestionService.convert_options_to_stored_format(None) is None


def test_convert_options_assigns_one_indexed_ids_preserving_text():
    out = QuestionService.convert_options_to_stored_format(
        [OptionCreate(text="Alpha"), OptionCreate(text="Beta")]
    )
    assert [(o.option_id, o.text) for o in out] == [(1, "Alpha"), (2, "Beta")]


# ----- create_question ------------------------------------------------------


def test_create_question_auto_generates_option_ids_and_returns_id():
    data = QuestionCreate(
        type="mcq",
        question_text=TEXT,
        options=[{"text": "Alpha"}, {"text": "Beta"}],
        correct_answers=[1],
    )
    with (
        patch("src.services.question_service.Question") as Q,
        patch(f"{SVC}.create", new=AsyncMock(return_value="newid")) as create,
    ):
        result = asyncio.run(QuestionService.create_question(data))
    assert result == "newid"
    # The service must turn text-only options into 1-indexed stored options.
    built = Q.call_args.kwargs["options"]
    assert [(o["option_id"], o["text"]) for o in built] == [(1, "Alpha"), (2, "Beta")]
    create.assert_awaited_once_with(Q.return_value)


def test_create_question_value_error_maps_to_400_with_detail():
    data = QuestionCreate(type="text", question_text=TEXT, sample_answer=TEXT)
    with (
        patch("src.services.question_service.Question"),
        patch(f"{SVC}.create", new=AsyncMock(side_effect=ValueError("bad value"))),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(QuestionService.create_question(data))
    assert exc.value.status_code == 400
    assert "bad value" in exc.value.detail


def test_create_question_unexpected_error_maps_to_500():
    data = QuestionCreate(type="text", question_text=TEXT, sample_answer=TEXT)
    with (
        patch("src.services.question_service.Question"),
        patch(f"{SVC}.create", new=AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(QuestionService.create_question(data))
    assert exc.value.status_code == 500
    assert "boom" in exc.value.detail


# ----- read/delete delegation (assert the wiring, not the mock) -------------


def test_get_all_questions_forwards_to_repo():
    sentinel = [object(), object()]
    with patch(f"{SVC}.get_all", new=AsyncMock(return_value=sentinel)) as repo:
        assert asyncio.run(QuestionService.get_all_questions()) is sentinel
    repo.assert_awaited_once_with()


def test_get_question_by_id_forwards_the_id():
    with patch(f"{SVC}.get_by_id", new=AsyncMock(return_value="q")) as repo:
        assert asyncio.run(QuestionService.get_question_by_id("abc")) == "q"
    repo.assert_awaited_once_with("abc")


def test_delete_question_forwards_the_id_and_returns_result():
    with patch(f"{SVC}.delete", new=AsyncMock(return_value=False)) as repo:
        assert asyncio.run(QuestionService.delete_question("abc")) is False
    repo.assert_awaited_once_with("abc")


# ----- update_question ------------------------------------------------------


def test_update_missing_question_returns_false_without_updating():
    with (
        patch(f"{SVC}.get_by_id", new=AsyncMock(return_value=None)),
        patch(f"{SVC}.update", new=AsyncMock()) as upd,
    ):
        assert (
            asyncio.run(QuestionService.update_question("x", QuestionUpdate())) is False
        )
    upd.assert_not_awaited()


def test_update_regenerates_option_ids_forwards_id_and_stamps_time():
    data = QuestionUpdate(
        options=[{"text": "Alpha"}, {"text": "Beta"}], correct_answers=[2]
    )
    with (
        patch(f"{SVC}.get_by_id", new=AsyncMock(return_value=_existing())),
        patch(f"{SVC}.update", new=AsyncMock(return_value=True)) as upd,
    ):
        assert asyncio.run(QuestionService.update_question("x", data)) is True
    qid, applied = upd.await_args.args
    assert qid == "x"
    assert [(o["option_id"], o["text"]) for o in applied["options"]] == [
        (1, "Alpha"),
        (2, "Beta"),
    ]
    assert applied["correct_answers"] == [2]
    assert "updated_at" in applied  # service stamps the update time


def test_update_drops_none_fields_before_persisting():
    # Only question_text is set; None fields must not reach the repo update.
    data = QuestionUpdate(question_text="A brand new question body")
    with (
        patch(f"{SVC}.get_by_id", new=AsyncMock(return_value=_existing())),
        patch(f"{SVC}.update", new=AsyncMock(return_value=True)) as upd,
    ):
        asyncio.run(QuestionService.update_question("x", data))
    applied = upd.await_args.args[1]
    assert applied["question_text"] == "A brand new question body"
    assert "options" not in applied and "correct_answers" not in applied


def test_update_invalid_for_type_maps_to_400():
    data = QuestionUpdate(correct_answers=[1, 2])  # two answers on an MCQ
    with (
        patch(f"{SVC}.get_by_id", new=AsyncMock(return_value=_existing("mcq"))),
        patch(f"{SVC}.update", new=AsyncMock()) as upd,
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(QuestionService.update_question("x", data))
    assert exc.value.status_code == 400
    upd.assert_not_awaited()  # rejected before persisting


# ----- _validate_update_for_type: MCQ ---------------------------------------

EXISTING_MCQ = {"options": [{"option_id": 1}, {"option_id": 2}], "correct_answers": [1]}


def test_validate_mcq_too_few_options():
    with pytest.raises(ValueError, match="at least 2 options"):
        QuestionService._validate_update_for_type(
            "mcq", EXISTING_MCQ, {"options": [{}]}
        )


def test_validate_mcq_wrong_count():
    with pytest.raises(ValueError, match="exactly one"):
        QuestionService._validate_update_for_type(
            "mcq", EXISTING_MCQ, {"correct_answers": [1, 2]}
        )


def test_validate_mcq_non_int():
    with pytest.raises(ValueError, match="integer"):
        QuestionService._validate_update_for_type(
            "mcq", EXISTING_MCQ, {"correct_answers": ["x"]}
        )


def test_validate_mcq_invalid_option_id():
    with pytest.raises(ValueError, match="not a valid option_id"):
        QuestionService._validate_update_for_type(
            "mcq", EXISTING_MCQ, {"correct_answers": [9]}
        )


def test_validate_mcq_ok_uses_existing_options():
    # update changes only the correct answer; option_ids come from existing doc
    QuestionService._validate_update_for_type(
        "mcq", EXISTING_MCQ, {"correct_answers": [2]}
    )


# ----- _validate_update_for_type: MULTI -------------------------------------

EXISTING_MULTI = {
    "options": [{"option_id": 1}, {"option_id": 2}, {"option_id": 3}],
    "correct_answers": [1, 2],
}


def test_validate_multi_too_few_options():
    with pytest.raises(ValueError, match="at least 2 options"):
        QuestionService._validate_update_for_type(
            "multi", EXISTING_MULTI, {"options": [{}]}
        )


def test_validate_multi_empty_correct():
    with pytest.raises(ValueError, match="at least one correct"):
        QuestionService._validate_update_for_type(
            "multi", EXISTING_MULTI, {"correct_answers": []}
        )


def test_validate_multi_non_int():
    with pytest.raises(ValueError, match="list of integers"):
        QuestionService._validate_update_for_type(
            "multi", EXISTING_MULTI, {"correct_answers": [1, "x"]}
        )


def test_validate_multi_duplicates():
    with pytest.raises(ValueError, match="duplicates"):
        QuestionService._validate_update_for_type(
            "multi", EXISTING_MULTI, {"correct_answers": [1, 1]}
        )


def test_validate_multi_invalid_option_id():
    with pytest.raises(ValueError, match="invalid option_id"):
        QuestionService._validate_update_for_type(
            "multi", EXISTING_MULTI, {"correct_answers": [9]}
        )


def test_validate_multi_all_correct_rejected():
    existing = {"options": [{"option_id": 1}, {"option_id": 2}], "correct_answers": [1]}
    with pytest.raises(ValueError, match="cannot have all options"):
        QuestionService._validate_update_for_type(
            "multi", existing, {"correct_answers": [1, 2]}
        )


def test_validate_multi_ok():
    QuestionService._validate_update_for_type(
        "multi", EXISTING_MULTI, {"correct_answers": [1, 3]}
    )


# ----- _validate_update_for_type: TRUE_FALSE & TEXT -------------------------


def test_validate_true_false_with_options():
    with pytest.raises(ValueError, match="should not have options"):
        QuestionService._validate_update_for_type(
            "true_false", {}, {"options": [{}, {}]}
        )


def test_validate_true_false_wrong_count():
    with pytest.raises(ValueError, match="exactly one"):
        QuestionService._validate_update_for_type(
            "true_false", {}, {"correct_answers": [True, False]}
        )


def test_validate_true_false_non_bool():
    with pytest.raises(ValueError, match="boolean"):
        QuestionService._validate_update_for_type(
            "true_false", {}, {"correct_answers": [1]}
        )


def test_validate_true_false_ok():
    QuestionService._validate_update_for_type(
        "true_false", {}, {"correct_answers": [True]}
    )


def test_validate_text_with_options():
    with pytest.raises(ValueError, match="should not have options"):
        QuestionService._validate_update_for_type("text", {}, {"options": [{}, {}]})


def test_validate_text_with_correct_answers():
    with pytest.raises(ValueError, match="should not have correct_answers"):
        QuestionService._validate_update_for_type("text", {}, {"correct_answers": [1]})


def test_validate_text_empty_sample():
    with pytest.raises(ValueError, match="non-empty"):
        QuestionService._validate_update_for_type("text", {}, {"sample_answer": "   "})


def test_validate_text_short_sample():
    with pytest.raises(ValueError, match="at least 10"):
        QuestionService._validate_update_for_type(
            "text", {}, {"sample_answer": "short"}
        )


def test_validate_text_ok():
    QuestionService._validate_update_for_type(
        "text", {}, {"sample_answer": "a long enough sample answer"}
    )


# ----- find_by_* (validation + argument cleaning) ---------------------------


def test_find_by_type_invalid_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.find_by_type("bogus"))
    assert exc.value.status_code == 400


def test_find_by_type_valid_forwards_type_and_limit():
    with patch(f"{SVC}.find_by_type", new=AsyncMock(return_value=["q"])) as repo:
        assert asyncio.run(QuestionService.find_by_type("mcq", limit=5)) == ["q"]
    repo.assert_awaited_once_with("mcq", 5)


def test_find_by_skill_empty_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.find_by_skill("   "))
    assert exc.value.status_code == 400


def test_find_by_skill_strips_before_forwarding():
    with patch(f"{SVC}.find_by_skill", new=AsyncMock(return_value=["q"])) as repo:
        asyncio.run(QuestionService.find_by_skill(" Python "))
    repo.assert_awaited_once_with("Python", 100)


def test_find_by_difficulty_invalid_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.find_by_difficulty("impossible"))
    assert exc.value.status_code == 400


def test_find_by_difficulty_valid_forwards():
    with patch(f"{SVC}.find_by_difficulty", new=AsyncMock(return_value=["q"])) as repo:
        asyncio.run(QuestionService.find_by_difficulty("easy"))
    repo.assert_awaited_once_with("easy", 100)


def test_find_by_tags_empty_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.find_by_tags([]))
    assert exc.value.status_code == 400


def test_find_by_tags_whitespace_only_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.find_by_tags(["  ", ""]))
    assert exc.value.status_code == 400


def test_find_by_tags_strips_and_drops_blanks():
    with patch(f"{SVC}.find_by_tags", new=AsyncMock(return_value=["q"])) as repo:
        asyncio.run(QuestionService.find_by_tags([" java ", "", "sql"]))
    repo.assert_awaited_once_with(["java", "sql"], 100)


# ----- filter_questions (validation branches only) --------------------------


def test_filter_no_criteria_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.filter_questions())
    assert exc.value.status_code == 400


def test_filter_invalid_type_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.filter_questions(question_type="bogus"))
    assert exc.value.status_code == 400


def test_filter_invalid_difficulty_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(QuestionService.filter_questions(difficulty="impossible"))
    assert exc.value.status_code == 400
