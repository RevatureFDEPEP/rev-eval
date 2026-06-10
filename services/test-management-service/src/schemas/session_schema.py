from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    """Request body for POST /sessions."""
    test_id: int = Field(..., description="ID of the quiz/test to start a session for")


class AnswerSubmit(BaseModel):
    """Request body for POST /sessions/{id}/answer.

    ``submitted_answers`` is the candidate's selection(s) for the *current*
    question: a list of option_ids for mcq/multi, or a single-element list for
    true_false. The server scores against the authoritative answer key; the
    key is never sent to the client.
    """
    submitted_answers: List[Any] = Field(default_factory=list)


class DraftSave(BaseModel):
    """Request body for PATCH /sessions/{id}/draft (W3-F4 autosave).

    ``answers`` is the candidate's full in-progress selection map keyed by
    question id (``{ question_id: [option_id, ...] }``). It is a last-write-wins
    crash-recovery snapshot: the server persists it verbatim but never scores it,
    and saving it does not advance ``current_index`` or change ``status``.
    """
    answers: Dict[str, List[int]] = Field(default_factory=dict)


class DraftSaveResult(BaseModel):
    """Response contract for PATCH /sessions/{id}/draft.

    Echoes the *unchanged* ``current_index``/``status`` so the client can confirm
    the autosave did not advance the session, plus the server save timestamp.
    """
    session_id: UUID
    status: str
    current_index: int
    saved_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SanitizedQuestion(BaseModel):
    """A question as exposed to the candidate — answer fields are stripped.

    correct_answers and sample_answer are deliberately omitted so the client
    (and the initial HTML) never carry the answer key. Scoring happens
    server-side in W3-F2.
    """
    id: str
    type: str
    question_text: str
    options: Optional[List[dict]] = None
    difficulty: Optional[str] = None
    image_url: Optional[str] = None


class SessionOut(BaseModel):
    """Response contract for POST /sessions (consumed server-side by W3-F3).

    The client never computes or stores timing — server_now/expires_at are
    authoritative.
    """
    session_id: UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    current_index: int
    total_questions: int
    question: Optional[SanitizedQuestion] = None
    # Present only when an existing ACTIVE session is reused (W3-F7 item 3):
    # the autosaved in-progress answers so the client can restore them.
    # None on a fresh mint — the response shape stays backward-compatible.
    draft_answers: Optional[Dict[str, List[int]]] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerResult(BaseModel):
    """Response contract for POST /sessions/{id}/answer.

    Deliberately score-free: per-question ``score`` / ``is_correct`` are
    persisted server-side but never returned, so a candidate cannot probe the
    answer key mid-exam (W3-F2 locked decision 1). Results are surfaced later
    from the answers table (W4-F1). The body carries only advance state.
    """
    session_id: UUID
    question_id: str
    current_index: int          # advanced past the question just answered
    total_questions: int
    status: str                 # "ACTIVE" or "SUBMITTED"
    submitted_at: Optional[datetime] = None
    next_question: Optional[SanitizedQuestion] = None

    model_config = ConfigDict(from_attributes=True)
