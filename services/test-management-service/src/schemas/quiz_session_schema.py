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


# ===== Answer submission (W3-F2) =====
class AnswerSubmit(BaseModel):
    """Request body for ``POST /test-sessions/{session_id}/answer``.

    ``submitted_answers`` is whatever the candidate selected (a list of option
    ids for mcq/multi, or a single-element list for true_false). It is scored
    server-side against the answer key fetched from question-management-service;
    the correct answers are NEVER part of this request or its response.
    """

    question_id: str
    submitted_answers: list = []


class AnswerResult(BaseModel):
    """Response for a scored answer.

    Carries only the candidate-safe outcome (score + correctness flag) and the
    server-authoritative session cursor/status. The correct-answer key is never
    included — only whether the submission was right and how much credit it
    earned.
    """

    question_id: str
    score: float
    is_correct: bool
    current_index: int
    status: str
