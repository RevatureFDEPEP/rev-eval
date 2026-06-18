"""Quiz-session creation endpoint (W3-F1, Part B).

``POST /v1/api/test-sessions/`` mints a server-authoritative quiz session:
it samples questions from question-management-service, freezes the ordered
question-id list, computes ``expires_at`` from the test duration, mints an
opaque session token, and persists the row. The candidate identity is taken
from the verified gateway identity (``X-User-*`` headers resolved by
``get_current_user_from_headers``) — never from the request body.

The pure bits (query-param building, duration/expiry math, token minting,
question mapping) live in ``src.services.quiz_session_helpers`` and are
unit-tested there; this module is the I/O orchestration shell.
"""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.session import get_db
from src.models.answer import Answer
from src.models.quiz_session import QuizSession
from src.models.skill import Skill
from src.models.test import Test
from src.models.test_skill import TestSkill
from src.models.test_submission import TestSubmission
from src.schemas.quiz_session_schema import (
    AnswerResult,
    AnswerSubmit,
    SessionCreate,
    SessionRead,
)
from src.scoring import score_question
from src.services.quiz_session_helpers import (
    build_sample_query,
    compute_expires_at,
    hash_session_token,
    map_sample_to_question,
    mint_session_token,
    resolve_duration_seconds,
)
from src.utils.dependencies import get_current_user_from_headers
from src.utils.http_client import get_qms_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-sessions", tags=["Test Sessions"])


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    """Create a quiz session for the authenticated candidate."""
    # Identity comes from the verified gateway claim, never the body.
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in authenticated identity",
        )
    user_id = int(user_id)

    correlation_id = x_correlation_id or uuid.uuid4().hex

    # 1) Fetch the test (404 if missing).
    test = (
        (await db.execute(select(Test).where(Test.id == body.test_id)))
        .scalars()
        .first()
    )
    if test is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test {body.test_id} not found",
        )

    # 2) If the caller supplies an assignment/submission link, verify it belongs
    # to this authenticated user and this test before any cross-service call.
    if body.submission_id is not None:
        submission = (
            (
                await db.execute(
                    select(TestSubmission).where(
                        TestSubmission.id == body.submission_id,
                        TestSubmission.test_id == body.test_id,
                        TestSubmission.user_id == user_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        if submission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )

    # 3) Idempotency / anti-re-sampling guard. Before any cross-service sampling
    # call, refuse a second active session for the same (user, test, submission):
    # without this a candidate could re-POST to re-roll the dice and keep the
    # easiest sampled set. We re-read the wall clock here (tz-aware UTC) and only
    # treat a row as blocking if it is still in_progress AND not yet expired — an
    # expired/abandoned attempt does not lock the candidate out.
    #
    # This check-then-act is not race-proof (two concurrent POSTs can both pass
    # the lookup). Closing the window needs a partial-unique constraint on
    # (user_id, test_id) WHERE status='in_progress' plus an Idempotency-Key —
    # tracked as a W3-F2/F5 follow-up.
    guard_now = datetime.now(UTC)
    active_session = (
        (
            await db.execute(
                select(QuizSession).where(
                    QuizSession.user_id == user_id,
                    QuizSession.test_id == body.test_id,
                    QuizSession.submission_id == body.submission_id,
                    QuizSession.status == "in_progress",
                    QuizSession.expires_at > guard_now,
                )
            )
        )
        .scalars()
        .first()
    )
    if active_session is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active session already exists for this test",
        )

    # 4) Resolve the test's skills (drives the sampling filter).
    skill_rows = (
        await db.execute(
            select(Skill.name)
            .join(TestSkill, TestSkill.skill_id == Skill.id)
            .where(TestSkill.test_id == body.test_id)
        )
    ).all()
    skills = [row[0] for row in skill_rows if row[0]]

    # 5) Sample questions from question-management-service.
    params = build_sample_query(test.number_of_questions, skills)
    client = get_qms_client()
    try:
        resp = await client.get(
            "/v1/api/questions/sample",
            params=params,
            headers={"X-Correlation-Id": correlation_id},
        )
    except httpx.RequestError as e:
        # Transport-level failure (DNS, connect, timeout, read): qms is
        # unreachable from our side -> 502. Never echo the upstream/exception.
        logger.warning(
            "qms sample transport error (correlation_id=%s): %s", correlation_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Question service is unavailable",
        ) from e

    # Distinguish an upstream *server* failure (their bug/outage -> 502, retryable)
    # from an upstream *client/contract* failure (our request was wrong, or qms
    # changed its contract -> 500, NOT retryable by the candidate). Either way we
    # surface a generic message and log the real status server-side.
    if resp.status_code >= 500:
        logger.warning(
            "qms sample upstream 5xx (correlation_id=%s, status=%s)",
            correlation_id,
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Question service is unavailable",
        )
    if resp.status_code >= 400:
        logger.error(
            "qms sample upstream 4xx (correlation_id=%s, status=%s)",
            correlation_id,
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question service contract error",
        )

    try:
        sampled = resp.json()
    except ValueError as e:
        # qms returned 2xx with a non-JSON / malformed body -> contract drift.
        logger.error(
            "qms sample returned non-JSON body (correlation_id=%s): %s",
            correlation_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question service contract error",
        ) from e

    if not sampled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No questions available for this test",
        )

    questions = [map_sample_to_question(doc) for doc in sampled]
    question_ids = [q.question_id for q in questions]

    # 6) Server-authoritative timing. Timezone-aware UTC (never naive utcnow) so
    # server_now/expires_at carry an explicit offset and the client's countdown
    # math is unambiguous; the two share one ``server_now`` read so the window is
    # exactly ``duration`` wide.
    server_now = datetime.now(UTC)
    duration_seconds = resolve_duration_seconds(test.duration)
    expires_at = compute_expires_at(server_now, duration_seconds)

    # 7) Mint opaque token + persist. The raw token is held in a local and
    # returned to the client exactly once; only its SHA-256 hash is stored, so a
    # DB dump cannot be replayed as a bearer token. ``raw_token`` never touches
    # the ORM row, so ``db.refresh`` (which reloads persisted columns) cannot
    # clobber it.
    # DEFER (W3-F2): this service trusts the gateway X-User-* headers and does not
    # re-verify the Bearer JWT; per-service JWT re-verification is a follow-up.
    raw_token = mint_session_token()
    session = QuizSession(
        session_token_hash=hash_session_token(raw_token),
        test_id=body.test_id,
        submission_id=body.submission_id,
        user_id=user_id,
        question_ids=question_ids,
        server_now=server_now,
        expires_at=expires_at,
        status="in_progress",
        current_index=0,
    )
    try:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    except SQLAlchemyError as e:
        # Postgres poisons the transaction on error — roll back before raising.
        # Never leak str(e) (it can carry SQL / column / value detail); log it.
        await db.rollback()
        logger.error(
            "failed to persist quiz session (correlation_id=%s): %s",
            correlation_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quiz session",
        ) from e

    return SessionRead(
        session_id=str(session.id),
        # The RAW token, returned exactly once; the DB holds only its hash.
        session_token=raw_token,
        test_id=session.test_id,
        user_id=session.user_id,
        status=session.status,
        current_index=session.current_index,
        server_now=session.server_now,
        expires_at=session.expires_at,
        first_question=questions[0] if questions else None,
        questions=questions,
    )


async def _fetch_correct_answers(question_id: str, correlation_id: str):
    """Fetch a question's CORRECT answer key from question-management-service.

    The answer key is the internal source of truth for scoring; it is NEVER
    returned to the quiz client. Maps any qms transport failure or 5xx to our
    own ``502`` envelope (never echoing the upstream body), and a contract drift
    (non-JSON / missing field) to a generic ``500``.
    """
    client = get_qms_client()
    try:
        resp = await client.get(
            f"/v1/api/questions/{question_id}",
            headers={"X-Correlation-Id": correlation_id},
        )
    except httpx.RequestError as e:
        logger.warning(
            "qms question fetch transport error (correlation_id=%s): %s",
            correlation_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Question service is unavailable",
        ) from e

    if resp.status_code == 404:
        # The question id is not one the answer flow should ever see (the session
        # froze a valid list), so a missing question is a contract/data error.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    if resp.status_code >= 500:
        logger.warning(
            "qms question fetch upstream 5xx (correlation_id=%s, status=%s)",
            correlation_id,
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Question service is unavailable",
        )
    if resp.status_code >= 400:
        logger.error(
            "qms question fetch upstream 4xx (correlation_id=%s, status=%s)",
            correlation_id,
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question service contract error",
        )

    try:
        doc = resp.json()
    except ValueError as e:
        logger.error(
            "qms question fetch non-JSON body (correlation_id=%s): %s",
            correlation_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question service contract error",
        ) from e

    # qms QuestionResponse exposes ``type`` and ``correct_answers``.
    return doc.get("type") or "", doc.get("correct_answers")


@router.post(
    "/{session_id}/answer",
    response_model=AnswerResult,
    status_code=status.HTTP_200_OK,
)
async def submit_answer(
    session_id: str,
    body: AnswerSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    """Score and persist one answer for the authenticated candidate's session.

    State machine: only an ``in_progress``, unexpired session accepts answers
    (otherwise 409). Idempotent on ``Idempotency-Key`` per session: a replay
    returns the prior result without re-scoring. The correct-answer key is
    fetched server-side and never returned.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in authenticated identity",
        )
    user_id = int(user_id)
    correlation_id = x_correlation_id or uuid.uuid4().hex

    # 1) Lock the session row for the read-modify-write (advance current_index /
    # flip status). with_for_update() serializes concurrent answers on Postgres;
    # it is a harmless no-op on SQLite.
    session = (
        (
            await db.execute(
                select(QuizSession)
                .where(QuizSession.id == session_id)
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )

    # Ownership / existence: a missing session is 404; a session owned by someone
    # else is 403 (don't leak existence beyond that — both are server-decided
    # from the verified identity, never the body).
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This session does not belong to you",
        )

    # 2) Idempotency replay: an existing (session_id, key) answer returns the
    # PRIOR result, scored exactly once — checked before any state/clock gate so
    # a retry after expiry still echoes the original outcome.
    if idempotency_key:
        prior = (
            (
                await db.execute(
                    select(Answer).where(
                        Answer.session_id == session_id,
                        Answer.idempotency_key == idempotency_key,
                    )
                )
            )
            .scalars()
            .first()
        )
        if prior is not None:
            return AnswerResult(
                question_id=prior.question_id,
                score=prior.score,
                is_correct=prior.is_correct,
                current_index=session.current_index,
                status=session.status,
            )

    # 3) State machine: lazily expire, then refuse anything not in_progress.
    now = datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if session.status == "in_progress" and expires_at is not None and now > expires_at:
        session.status = "expired"
        try:
            await db.commit()
        except SQLAlchemyError:  # pragma: no cover - defensive
            await db.rollback()
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is {session.status}; no further answers accepted",
        )

    # 4) The client may only answer the question at the server-authoritative
    # cursor. If a retry lands after another request advanced the index, refuse
    # instead of scoring the stale question against the wrong slot.
    question_ids = session.question_ids or []
    current_index = session.current_index or 0
    if not question_ids or current_index >= len(question_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session has no remaining questions",
        )
    expected_question_id = str(question_ids[current_index])
    if body.question_id != expected_question_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Answer submitted for wrong question index",
        )

    # 5) Score against the server-fetched answer key (never trusted from client).
    qtype, correct_answers = await _fetch_correct_answers(
        body.question_id, correlation_id
    )
    result = score_question(qtype, correct_answers, body.submitted_answers)

    # 6) Persist the answer + advance the cursor; flip to submitted on the last
    # question. One commit so the answer and the cursor move atomically.
    answer = Answer(
        session_id=session_id,
        question_id=body.question_id,
        submitted_answers=body.submitted_answers,
        score=result.score,
        is_correct=result.is_correct,
        idempotency_key=idempotency_key,
    )
    session.current_index = (session.current_index or 0) + 1
    if question_ids and session.current_index >= len(question_ids):
        session.status = "submitted"
        # Stamp the submission time from the same server-authoritative clock the
        # expiry gate used above (never a client value). W4-F1 reporting sorts on
        # this; it is set exactly once, only on this submit transition.
        session.submitted_at = now

    try:
        db.add(answer)
        await db.commit()
        await db.refresh(session)
    except IntegrityError as e:
        # A unique-constraint hit means a concurrent writer beat us (same
        # idempotency key, or this question was already answered). Roll back and
        # return the winning row's result rather than 500.
        await db.rollback()
        winner = await _existing_answer(
            db, session_id, body.question_id, idempotency_key
        )
        if winner is not None:
            fresh = (
                (
                    await db.execute(
                        select(QuizSession).where(QuizSession.id == session_id)
                    )
                )
                .scalars()
                .first()
            )
            return AnswerResult(
                question_id=winner.question_id,
                score=winner.score,
                is_correct=winner.is_correct,
                current_index=fresh.current_index if fresh else session.current_index,
                status=fresh.status if fresh else session.status,
            )
        logger.error(
            "answer persist integrity error with no winner (correlation_id=%s): %s",
            correlation_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Answer already recorded for this question",
        ) from e
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "failed to persist answer (correlation_id=%s): %s", correlation_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record answer",
        ) from e

    return AnswerResult(
        question_id=body.question_id,
        score=result.score,
        is_correct=result.is_correct,
        current_index=session.current_index,
        status=session.status,
    )


async def _existing_answer(db, session_id, question_id, idempotency_key):
    """Fetch the winning answer row after an IntegrityError (idempotency key
    first, then the per-question constraint)."""
    if idempotency_key:
        row = (
            (
                await db.execute(
                    select(Answer).where(
                        Answer.session_id == session_id,
                        Answer.idempotency_key == idempotency_key,
                    )
                )
            )
            .scalars()
            .first()
        )
        if row is not None:
            return row
    return (
        (
            await db.execute(
                select(Answer).where(
                    Answer.session_id == session_id,
                    Answer.question_id == question_id,
                )
            )
        )
        .scalars()
        .first()
    )
