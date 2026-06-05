import pytest
from pydantic import ValidationError
from src.models.question import Option, OptionCreate, QuestionType


class TestQuestionTypeEnum:
    @pytest.mark.parametrize("value,member", [
        ("mcq", QuestionType.MCQ),
        ("multi", QuestionType.MULTI),
        ("true_false", QuestionType.TRUE_FALSE),
        ("text", QuestionType.TEXT),
    ])
    def test_enum_values(self, value, member):
        assert QuestionType(value) == member

    def test_four_types_defined(self):
        assert len(QuestionType) == 4

    @pytest.mark.parametrize("qt", list(QuestionType))
    def test_all_are_str_subclass(self, qt):
        assert isinstance(qt, str)


class TestOptionCreate:
    @pytest.mark.parametrize("text,expected", [
        ("Valid option", "Valid option"),
        ("  Whitespace stripped  ", "Whitespace stripped"),
        ("Single word", "Single word"),
    ])
    def test_text_is_stripped(self, text, expected):
        opt = OptionCreate(text=text)
        assert opt.text == expected

    @pytest.mark.parametrize("bad_text", ["", "   "])
    def test_empty_text_raises(self, bad_text):
        with pytest.raises((ValueError, ValidationError)):
            OptionCreate(text=bad_text)

    def test_long_text_within_max(self):
        opt = OptionCreate(text="A" * 500)
        assert len(opt.text) == 500

    def test_text_exceeding_max_rejected(self):
        with pytest.raises(ValidationError):
            OptionCreate(text="A" * 501)


class TestOption:
    def test_valid_option(self):
        opt = Option(option_id=1, text="Answer choice")
        assert opt.option_id == 1
        assert opt.text == "Answer choice"

    def test_option_id_zero_rejected(self):
        with pytest.raises(ValidationError):
            Option(option_id=0, text="Invalid")

    @pytest.mark.parametrize("option_id", [1, 2, 5, 10, 100])
    def test_valid_option_ids(self, option_id):
        opt = Option(option_id=option_id, text="Some text")
        assert opt.option_id == option_id

    def test_text_is_stripped(self):
        opt = Option(option_id=1, text="  stripped  ")
        assert opt.text == "stripped"
