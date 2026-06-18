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

from pydantic import BaseModel, Field


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
    questions: list[QuizQuestionOut] = Field(default_factory=list)


# ===== Answer submission (W3-F2) =====
class AnswerSubmit(BaseModel):
    """Request body for ``POST /test-sessions/{session_id}/answer``.

    ``submitted_answers`` is scored server-side against the answer key fetched
    from question-management-service; the correct answers are NEVER part of this
    request or its response.

    Answer-encoding contract (MUST match qms — the scoring engine compares the
    two sets element-for-element with no coercion, so a mismatch silently scores
    0.0):

    * ``mcq`` / ``multi`` — a list of **1-indexed integer ``option_id``s**, the
      same 1-indexed positions qms stores in ``correct_answers`` (qms options are
      numbered from 1). Send ``[2]`` for the second option, not ``[1]``
      (0-indexed) and not the option *text*. mcq carries exactly one id; multi
      carries one or more.
    * ``true_false`` — a single-element list holding a ``bool`` (``[true]`` /
      ``[false]``), matching the boolean qms stores.
    * ``text`` — free-text is not auto-scored in W3-F2 (essay/short-answer is a
      placeholder); send the raw string if present.

    The TestRunner submit path (W3-F3 / #151) MUST emit ``option_id``s here.
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
