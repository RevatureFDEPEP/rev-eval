from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

from src.models.quiz_session import QuizSessionStatus


def _to_utc_iso(value: datetime | None) -> str | None:
    """Serialize a naive datetime (stored as UTC by repo convention) with an
    explicit +00:00 offset, so a client parses it as UTC rather than local time.

    The DB stores naive UTC and Pydantic would otherwise emit an offset-less ISO
    string (e.g. "2026-06-13T10:00:00"), which JS `new Date()` reads as *local*.
    Shared across the quiz-taking responses (W3-F1/F2/F4)."""
    return value.replace(tzinfo=UTC).isoformat() if value is not None else None


# Datetime fields that serialize with an explicit UTC offset (see _to_utc_iso).
# when_used="json" leaves Python-mode model_dump() returning datetime objects;
# only JSON output (FastAPI responses) gets the offset string.
UtcDatetime = Annotated[
    datetime, PlainSerializer(_to_utc_iso, return_type=str, when_used="json")
]
OptionalUtcDatetime = Annotated[
    datetime | None,
    PlainSerializer(_to_utc_iso, return_type=str | None, when_used="json"),
]

# Bounds for the advisory draft payload. A real quiz has a handful of questions,
# each with a few selectable options — these caps keep an authenticated client
# from persisting an unbounded JSON blob to its session row (the 10MB nginx body
# limit exists for image uploads and is far too loose for an answer map).
_MAX_DRAFT_QUESTIONS = 200
_MAX_OPTIONS_PER_QUESTION = 50
DraftOptionIds = Annotated[
    list[Annotated[int, Field(ge=0)]], Field(max_length=_MAX_OPTIONS_PER_QUESTION)
]
DraftAnswers = Annotated[
    dict[str, DraftOptionIds], Field(max_length=_MAX_DRAFT_QUESTIONS)
]


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
    server_now: (
        UtcDatetime  # server clock at response time; client never computes timing
    )
    expires_at: UtcDatetime
    total_questions: int
    current_index: int
    question: ParticipantQuestion
    # Advisory autosave snapshot (question_id -> option_ids), echoed so a resumed
    # session can rehydrate the client's in-progress selection. None on a fresh
    # session or when nothing has been autosaved yet (W3-F4).
    draft_answers: dict[str, list[int]] | None = None
    # Stored monotonic draft version (0 if nothing saved yet). The client seeds
    # its autosave counter from this so resumed saves keep increasing past the
    # last persisted version rather than restarting and being rejected (W3-F4).
    draft_version: int = 0


class SessionCreateResponse(SessionBaseResponse):
    session_token: (
        str  # TODO(W3-F2): validated as a bearer credential on answer-submit endpoints
    )


class SessionStateResponse(SessionBaseResponse):
    pass


class DraftSaveRequest(BaseModel):
    """Advisory autosave payload: the full in-progress answer map.

    `client_version` is a strictly increasing stamp (per session-life, seeded
    from the stored draft_version on resume). The server applies the write only
    when it exceeds the stored version, so a late stale snapshot can't clobber a
    fresher one under out-of-order delivery. question_id -> selected option_ids.
    Bounded (see DraftAnswers) so an advisory autosave can't write an unbounded
    blob; an over-cap payload is rejected with 422 (semantic — the client halts).
    """

    answers: DraftAnswers
    client_version: int = Field(ge=1)


class DraftSaveResponse(BaseModel):
    """Acknowledges an autosave without advancing the session.

    Echoes the UNCHANGED current_index/status so the client can confirm the
    draft did not score or advance, plus saved_at for the save-status UI.
    `applied` is False when the monotonic guard rejected a stale snapshot (a
    fresher version already won) — still a 200, not an error; the client's data
    is safe either way. `draft_version` is the now-current stored version.
    """

    session_id: str
    status: QuizSessionStatus
    current_index: int
    saved_at: UtcDatetime
    applied: bool = True
    draft_version: int = 0
