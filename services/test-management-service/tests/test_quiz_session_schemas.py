"""Schema tests: the participant-facing question view must never carry answers."""

from src.schemas.quiz_session_schema import ParticipantQuestion


def test_participant_question_drops_answer_fields():
    # Feed a full question-management-service payload, answers included.
    raw = {
        "id": "q1",
        "type": "mcq",
        "question_text": "What is 2 + 2?",
        "options": [{"option_id": 1, "text": "4"}],
        "difficulty": "easy",
        "index": 0,
        # answer fields that must not survive
        "correct_answers": [1],
        "sample_answer": "4",
        "answer_explanation": "addition",
    }
    pq = ParticipantQuestion(**raw)
    dumped = pq.model_dump()

    assert dumped["id"] == "q1"
    assert dumped["options"] == [{"option_id": 1, "text": "4"}]
    assert "correct_answers" not in dumped
    assert "sample_answer" not in dumped
    assert "answer_explanation" not in dumped


def test_participant_question_options_optional():
    pq = ParticipantQuestion(
        id="q2",
        type="true_false",
        question_text="The sky is blue.",
        difficulty="easy",
        index=1,
    )
    assert pq.options is None
