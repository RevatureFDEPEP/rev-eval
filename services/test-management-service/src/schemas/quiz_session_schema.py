"""Pydantic schemas for the quiz-session backend (W3-F1, Part B).

These are the canonical request/response shapes the frontend matches (the
client mirrors the server, never the reverse). They intentionally import only
pydantic + stdlib — no ORM models, no Mongo — so they are pure-unit-testable
and stay inside the coverage gate.

``QuizQuestionOut`` is the *quiz-safe* question projection: it never carries
``correct_answers``/``sample_answer``, so the answer key cannot leak to a
candidate over the wire.
"""

from datetime import datetime

from pydantic import BaseModel


# ===== Request =====
class SessionCreate(BaseModel):
    test_id: int
    submission_id: int | None = None


# ===== Question (NEVER include correct answers) =====
class QuizQuestionOut(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    difficulty: str
    options: list[dict] | None = None


# ===== Response =====
class SessionRead(BaseModel):
    session_id: str
    session_token: str
    test_id: int
    user_id: int
    status: str
    current_index: int
    server_now: datetime
    expires_at: datetime
    first_question: QuizQuestionOut | None
