from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.grading_schema import (
    GradedAnswerOut,
    GradeRequest,
    GradingQueueOut,
)
from src.schemas.session_schema import (
    AnswerResult,
    AnswerSubmit,
    DraftSave,
    DraftSaveResult,
    SessionCreate,
    SessionOut,
)
from src.services.grading_service import (
    AnswerNotFoundError,
    AnswerNotPendingError,
    GradingService,
)
from src.services.session_service import (
    EmptyQuestionBankError,
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
    SessionService,
    SessionTerminalError,
)
from src.utils.dependencies import (
    get_current_trainer,
    get_current_user_from_headers,
)
from src.utils.question_client import QuestionServiceError

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# --- Trainer manual-grading (W5-F1) -----------------------------------------
# Registered before the dynamic /{session_id}/... routes; the static
# "grading-queue" segment must not be shadowed by a path parameter.


@router.get("/grading-queue", response_model=GradingQueueOut)
async def grading_queue(
    test_id: Optional[int] = Query(None, description="Filter by test id"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db),
):
    """TRAINER-only: list free-text answers awaiting a manual grade (W5-F1),
    enriched with each question's prompt + sample answer."""
    return await GradingService.list_queue(
        db, test_id=test_id, page=page, size=size
    )


@router.post(
    "/{session_id}/answers/{question_index}/grade",
    response_model=GradedAnswerOut,
)
async def grade_answer(
    session_id: UUID,
    question_index: int,
    grade_in: GradeRequest,
    current_user: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db),
):
    """TRAINER-only: set a free-text answer's score (0..1) + optional feedback
    and recompute the session's needs_grading flag (W5-F1). The candidate's
    attempt score (computed on-read) then includes the graded answer."""
    try:
        return await GradingService.grade_answer(
            db,
            session_id,
            question_index,
            grade_in.score,
            grade_in.feedback,
            current_user.get("id"),
        )
    except AnswerNotFoundError:
        raise HTTPException(status_code=404, detail="Answer not found") from None
    except AnswerNotPendingError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        ) from None


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: SessionCreate,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Start a quiz session: mint an opaque token, record server-authoritative
    timing, sample the question set from question-management-service, and
    return the first (sanitized) question."""
    user_id = current_user.get("id")
    try:
        return await SessionService.create_session(db, session_in.test_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found") from None
    except EmptyQuestionBankError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from None
    except QuestionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"question-management-service unavailable: {e}",
        ) from None


@router.patch("/{session_id}/draft", response_model=DraftSaveResult)
async def save_draft(
    session_id: UUID,
    draft_in: DraftSave,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Autosave the candidate's in-progress answers (W3-F4).

    Persists a last-write-wins crash-recovery snapshot **without** scoring or
    advancing the session — ``current_index``/``status`` are returned unchanged.
    Terminal/expired sessions reject with 409 (a semantic error the client must
    surface and halt on, never retry)."""
    user_id = current_user.get("id")
    try:
        return await SessionService.save_draft(
            db, session_id, user_id, draft_in.answers
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    except SessionForbiddenError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except (SessionTerminalError, SessionExpiredError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.post("/{session_id}/answer", response_model=AnswerResult)
async def submit_answer(
    session_id: UUID,
    answer_in: AnswerSubmit,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Client-generated key making this answer submission "
        "retry-safe (required).",
    ),
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Score the candidate's answer to the current question and advance the
    session. Pessimistically locked, idempotent (via the required
    ``Idempotency-Key`` header), and state-machine enforced — submitted/expired
    sessions reject further mutations with 409. The per-question score is
    recorded server-side but not returned."""
    if not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key header must not be blank",
        )
    user_id = current_user.get("id")
    try:
        return await SessionService.submit_answer(
            db,
            session_id,
            user_id,
            answer_in.submitted_answers,
            idempotency_key,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    except SessionForbiddenError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except (SessionTerminalError, SessionExpiredError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    except QuestionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"question-management-service unavailable: {e}",
        ) from None
