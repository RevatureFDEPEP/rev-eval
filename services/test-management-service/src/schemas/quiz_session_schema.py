from datetime import datetime

from pydantic import BaseModel

from src.models.quiz_session import QuizSessionStatus


class SessionCreateRequest(BaseModel):
    test_id: int


class ParticipantQuestion(BaseModel):
    """
    Answer-free view of a question sent to a participant.

    This is an allow-list: it deliberately has no `correct_answers`,
    `sample_answer`, or `answer_explanation` fields, so answer data can never
    leak to the participant even if the upstream question payload contains it.
    """

    id: str
    type: str
    question_text: str
    options: list[dict] | None = None
    difficulty: str | None = None
    index: int


class SessionCreateResponse(BaseModel):
    session_id: str
    session_token: str
    status: QuizSessionStatus
    server_now: datetime  # server clock at response time; client never computes timing
    expires_at: datetime
    total_questions: int
    current_index: int
    question: ParticipantQuestion


class SessionStateResponse(BaseModel):
    session_id: str
    status: QuizSessionStatus
    server_now: datetime
    expires_at: datetime
    total_questions: int
    current_index: int
    question: ParticipantQuestion
