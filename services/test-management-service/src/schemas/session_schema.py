# src/schemas/session_schema.py
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for starting a quiz session."""
    test_id: int


class SanitizedQuestion(BaseModel):
    """A question as exposed to the candidate — answer fields stripped.

    Built from question-management-service's ``QuestionPublic`` (already
    answer-free at the ``/sample`` endpoint) or by sanitizing a full question
    body server-side before it crosses to the client. Never carries
    ``correct_answers``/``sample_answer``/``answer_explanation``.
    """
    id: str
    type: str
    question_text: str
    options: list[dict] | None = None
    difficulty: str | None = None


class SessionResponse(BaseModel):
    """Response contract for a freshly created quiz session.

    Sequential-reveal model: only the **current** question body is returned.
    Subsequent questions are delivered one at a time by the answer endpoint
    (``next_question``), so future question bodies never reach the client.
    ``current_index``/``total_questions`` let the client render progress without
    holding the whole bank; ``draft_answers`` seeds a resumed session (W3-F4).
    """
    session_id: str
    session_token: str
    server_now: datetime
    expires_at: datetime
    current_index: int
    total_questions: int
    question: SanitizedQuestion | None = Field(
        None, description="Body of the session's current question (answer key stripped)"
    )
    draft_answers: dict[str, list[int]] | None = Field(
        None, description="Autosaved partial answers, present only on a resumed session"
    )
