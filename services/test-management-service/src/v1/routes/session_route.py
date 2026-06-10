from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.session_schema import (
    AnswerResult,
    AnswerSubmit,
    DraftSave,
    DraftSaveResult,
    SessionCreate,
    SessionOut,
)
from src.services.session_service import (
    EmptyQuestionBankError,
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
    SessionService,
    SessionTerminalError,
)
from src.utils.dependencies import get_current_user_from_headers
from src.utils.question_client import QuestionServiceError

router = APIRouter(prefix="/sessions", tags=["Sessions"])


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
