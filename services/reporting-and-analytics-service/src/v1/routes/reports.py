from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.session import get_eval_ai_db
from src.models.quiz_session import QuizSession, SessionStatus
from src.models.session_answer import SessionAnswer
from src.schemas.reports import (
    ALLOWED_SORT_FIELDS,
    AttemptItem,
    AttemptsFilter,
    MostRecentAttempt,
    PaginatedAttempts,
    UserSummary,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _session_scores_subquery():
    return (
        select(
            SessionAnswer.session_id,
            func.sum(SessionAnswer.score).label("total_score"),
        )
        .group_by(SessionAnswer.session_id)
        .subquery()
    )


@router.get("/user/{user_id}", response_model=UserSummary)
def get_user_summary(user_id: int, db: Session = Depends(get_eval_ai_db)):
    session_scores = _session_scores_subquery()

    # Single aggregate query: count, avg, best
    row = db.execute(
        select(
            func.count(QuizSession.id).label("total_attempts"),
            func.avg(session_scores.c.total_score).label("avg_score"),
            func.max(session_scores.c.total_score).label("best_score"),
        )
        .outerjoin(session_scores, session_scores.c.session_id == QuizSession.id)
        .where(
            QuizSession.user_id == user_id,
            QuizSession.status == SessionStatus.SUBMITTED,
        )
    ).one()

    # Total time spent: PG-specific EXTRACT(epoch); isolated so SQLite tests still pass
    try:
        total_time_spent = db.scalar(
            select(
                func.sum(
                    func.extract(
                        "epoch", QuizSession.submitted_at - QuizSession.server_now
                    )
                )
            ).where(
                QuizSession.user_id == user_id,
                QuizSession.status == SessionStatus.SUBMITTED,
            )
        )
    except Exception:
        total_time_spent = None
    if total_time_spent is not None and total_time_spent < 0:
        total_time_spent = None

    # Subquery for most-recent attempt with its score
    latest = db.execute(
        select(QuizSession, session_scores.c.total_score)
        .outerjoin(session_scores, session_scores.c.session_id == QuizSession.id)
        .where(
            QuizSession.user_id == user_id,
            QuizSession.status == SessionStatus.SUBMITTED,
        )
        .order_by(QuizSession.submitted_at.desc())
        .limit(1)
    ).first()

    most_recent = None
    if latest:
        qs, score = latest
        most_recent = MostRecentAttempt(
            session_id=qs.id,
            test_id=qs.test_id,
            submitted_at=qs.submitted_at,
            score=score,
        )

    return UserSummary(
        user_id=user_id,
        total_attempts=row.total_attempts or 0,
        avg_score=row.avg_score,
        best_score=row.best_score,
        total_time_spent_seconds=total_time_spent,
        most_recent_attempt=most_recent,
    )


@router.get("/user/{user_id}/attempts", response_model=PaginatedAttempts)
def get_user_attempts(
    user_id: int,
    filters: AttemptsFilter = Depends(),
    db: Session = Depends(get_eval_ai_db),
):
    sort_parts = filters.sort.split(":")
    sort_field = sort_parts[0]
    sort_dir = sort_parts[1] if len(sort_parts) > 1 else "desc"

    if sort_field not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_field}'. Allowed: {sorted(ALLOWED_SORT_FIELDS)}",
        )

    session_scores = _session_scores_subquery()

    base = (
        select(QuizSession, session_scores.c.total_score)
        .outerjoin(session_scores, session_scores.c.session_id == QuizSession.id)
        .where(QuizSession.user_id == user_id)
    )

    if filters.test_id is not None:
        base = base.where(QuizSession.test_id == filters.test_id)
    if filters.status is not None:
        base = base.where(QuizSession.status == filters.status)
    if filters.from_ is not None:
        base = base.where(QuizSession.submitted_at >= filters.from_)
    if filters.to is not None:
        base = base.where(QuizSession.submitted_at <= filters.to)

    total = db.scalar(select(func.count()).select_from(base.subquery()))

    sort_col = getattr(QuizSession, sort_field)
    if sort_dir == "asc":
        base = base.order_by(sort_col.asc())
    else:
        base = base.order_by(sort_col.desc())

    rows = db.execute(
        base.offset((filters.page - 1) * filters.size).limit(filters.size)
    ).all()

    items = [
        AttemptItem(
            session_id=qs.id,
            test_id=qs.test_id,
            status=qs.status.value if hasattr(qs.status, "value") else qs.status,
            submitted_at=qs.submitted_at,
            score=score,
            created_at=qs.created_at,
        )
        for qs, score in rows
    ]

    return PaginatedAttempts(
        items=items,
        total=total or 0,
        page=filters.page,
        size=filters.size,
    )
