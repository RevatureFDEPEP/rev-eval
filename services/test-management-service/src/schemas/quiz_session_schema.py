from datetime import datetime

from pydantic import BaseModel

from src.models.quiz_session import QuizSessionStatus


class SessionCreateRequest(BaseModel):
    test_id: int


class QuestionOption(BaseModel):
    """Allow-list for a single MCQ option — no is_correct or similar keys."""

    option_id: int
    text: str


class ParticipantQuestion(BaseModel):
    """
    Answer-free view of a question sent to a participant.

    This is an allow-list: it deliberately has no `correct_answers`,
    `sample_answer`, or `answer_explanation` fields, so answer data can never
    leak to the participant even if the upstream question payload contains it.
    `options` is typed to QuestionOption so nested answer keys (is_correct,
    correct, etc.) are stripped by Pydantic rather than passed through.
    """

    id: str
    type: str
    question_text: str
    options: list[QuestionOption] | None = None
    difficulty: str | None = None
    index: int


class SessionBaseResponse(BaseModel):
    session_id: str
    status: QuizSessionStatus
    server_now: datetime  # server clock at response time; client never computes timing
    expires_at: datetime
    total_questions: int
    current_index: int
    question: ParticipantQuestion


class SessionCreateResponse(SessionBaseResponse):
    session_token: (
        str  # TODO(W3-F2): validated as a bearer credential on answer-submit endpoints
    )


class SessionStateResponse(SessionBaseResponse):
    pass
