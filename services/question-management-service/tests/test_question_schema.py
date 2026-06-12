import pytest
from pydantic import ValidationError

from src.models.question import OptionCreate, QuestionType
from src.schemas.question import QuestionCreate


def _opts(*texts: str) -> list[OptionCreate]:
    return [OptionCreate(text=t) for t in texts]


@pytest.mark.parametrize(
    "qtype,question_text,options,correct_answers,sample_answer",
    [
        (
            QuestionType.MCQ,
            "What does JVM stand for?",
            _opts(
                "Just Virtual Machine",
                "Java Virtual Machine",
                "Java Version Manager",
                "JVM Manager",
            ),
            [2],
            None,
        ),
        (
            QuestionType.TEXT,
            "Explain polymorphism in Java in your own words.",
            None,
            None,
            "Polymorphism lets objects of different types be used through a shared interface.",
        ),
    ],
)
def test_question_create_accepts_valid_mcq_and_text_payloads(
    qtype, question_text, options, correct_answers, sample_answer
):
    q = QuestionCreate(
        type=qtype,
        question_text=question_text,
        options=options,
        correct_answers=correct_answers,
        sample_answer=sample_answer,
    )
    assert q.question_text == question_text


@pytest.mark.parametrize(
    "options,correct_answers",
    [
        (
            # correct_answer index exceeds option count
            _opts("London", "Paris", "Berlin", "Madrid"),
            [10],
        ),
        (
            # duplicate option texts
            _opts("Java", "Java", "Kotlin", "Scala"),
            [1],
        ),
    ],
)
def test_question_create_rejects_invalid_mcq_payloads(options, correct_answers):
    with pytest.raises(ValidationError):
        QuestionCreate(
            type=QuestionType.MCQ,
            question_text="Which language runs on the JVM?",
            options=options,
            correct_answers=correct_answers,
        )
