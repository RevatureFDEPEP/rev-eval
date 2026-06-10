import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src import scoring
from src.models.answer import Answer
from src.models.idempotency_key import IdempotencyKey
from src.models.session import Session, SessionStatus
from src.repositories.answer_repository import AnswerRepository
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.session_repository import SessionRepository
from src.schemas.session_schema import (
    AnswerResult,
    DraftSaveResult,
    SanitizedQuestion,
    SessionOut,
)
from src.utils import question_client

logger = logging.getLogger(__name__)

# Fallback session length when a test has no configured duration.
_DEFAULT_DURATION = timedelta(seconds=3600)
_DEFAULT_QUESTION_COUNT = 20


class EmptyQuestionBankError(Exception):
    """Raised when the question bank returns no questions to sample."""


class SessionNotFoundError(Exception):
    """Raised when no session exists for the given id (→ 404)."""


class SessionForbiddenError(Exception):
    """Raised when a session belongs to a different user (→ 403)."""


class SessionTerminalError(Exception):
    """Raised when answering a session that is already submitted/expired,
    or otherwise past its last question (→ 409). Terminal states are
    immutable."""


class SessionExpiredError(Exception):
    """Raised when a session's expires_at has passed (→ 409). The session is
    transitioned to EXPIRED as a side effect."""


def _question_id(q: dict) -> str:
    """QuestionResponse serializes its id under the `_id` alias by default;
    accept either key."""
    return str(q.get("id") or q.get("_id"))


def _sanitize(q: dict) -> SanitizedQuestion:
    """Strip answer fields (correct_answers, sample_answer) before exposing a
    question to the candidate."""
    return SanitizedQuestion(
        id=_question_id(q),
        type=q["type"],
        question_text=q["question_text"],
        options=q.get("options"),
        difficulty=q.get("difficulty"),
        image_url=q.get("image_url"),
    )


class SessionService:

    @staticmethod
    async def _resume_session(db: AsyncSession, session: Session) -> Optional[SessionOut]:
        """Rebuild a SessionOut from an existing ACTIVE row (W3-F7 item 3).

        Returns None — after flipping the row to EXPIRED — when its
        ``expires_at`` has already passed (same side-effect convention as
        ``submit_answer``), so the caller proceeds to mint a fresh session.

        The response anchors ``server_now`` at *now* against the **original**
        ``expires_at``, so the client countdown shows true remaining time;
        ``current_index`` and the autosaved ``draft_answers`` ride along for
        refresh-recovery.
        """
        now = datetime.utcnow()
        if session.expires_at is not None and session.expires_at < now:
            session.status = SessionStatus.EXPIRED
            await SessionRepository.flush(db, session)
            await db.commit()
            return None

        question_ids = list(session.question_ids or [])
        question = None
        if session.current_index < len(question_ids):
            q = await question_client.get_question(
                question_ids[session.current_index]
            )
            question = _sanitize(q)

        logger.info(
            "session reused: session_id=%s test_id=%s user_id=%s index=%d",
            session.session_id, session.test_id, session.user_id,
            session.current_index,
        )
        return SessionOut(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=now,
            expires_at=session.expires_at,
            current_index=session.current_index,
            total_questions=len(question_ids),
            question=question,
            draft_answers=session.draft_answers,
        )

    @staticmethod
    async def create_session(db: AsyncSession, test_id: int, user_id: int) -> SessionOut:
        """Mint a quiz session: server-authoritative timing, a fixed sampled
        question set, and the first (sanitized) question. Persists the row
        before responding.

        Reuse semantic (W3-F7 item 3): at most one ACTIVE session per
        (user, test). An existing live session is returned as-is (question set,
        clock, draft answers intact) instead of minting a duplicate — a page
        refresh must not re-sample questions or reset the countdown. The
        partial unique index (Alembic 0007) backstops the lookup race; the
        loser of a concurrent double-POST serves the winner's row, not a 500.
        """
        test = await SessionRepository.get_test(db, test_id)
        if test is None:
            raise ValueError("Test not found")

        existing = await SessionRepository.get_active_for_user_test(
            db, user_id, test_id
        )
        if existing is not None:
            resumed = await SessionService._resume_session(db, existing)
            if resumed is not None:
                return resumed

        # Server-authoritative timing (tz-naive UTC, matching repo convention).
        server_now = datetime.utcnow()
        duration = test.duration or _DEFAULT_DURATION
        expires_at = server_now + duration

        size = test.number_of_questions or _DEFAULT_QUESTION_COUNT
        questions = await question_client.sample_questions(size)
        if not questions:
            raise EmptyQuestionBankError(
                "No questions available to start a session"
            )

        # Mongo $sample may emit duplicate documents — dedupe (order-preserving)
        # so a candidate is never asked the same question twice (W3-F7 item 8).
        seen: set[str] = set()
        unique_questions = []
        for q in questions:
            qid = _question_id(q)
            if qid not in seen:
                seen.add(qid)
                unique_questions.append(q)
        questions = unique_questions

        if len(questions) < size:
            # Short fill (small bank and/or duplicates dropped) — visible, not silent.
            logger.warning(
                "session short-filled: test_id=%s requested=%d got=%d",
                test_id, size, len(questions),
            )

        question_ids = [_question_id(q) for q in questions]
        first_question = _sanitize(questions[0])

        session = Session(
            session_id=uuid4(),
            test_id=test_id,
            user_id=user_id,
            session_token=secrets.token_hex(32),
            server_now=server_now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            current_index=0,
            question_ids=question_ids,
        )
        try:
            await SessionRepository.create(db, session)
        except IntegrityError:
            # Lost the uq_sessions_active_user_test race — another request
            # created the ACTIVE session between our lookup and insert.
            await db.rollback()
            winner = await SessionRepository.get_active_for_user_test(
                db, user_id, test_id
            )
            if winner is not None:
                resumed = await SessionService._resume_session(db, winner)
                if resumed is not None:
                    return resumed
            raise
        logger.info(
            "session created: session_id=%s test_id=%s user_id=%s questions=%d",
            session.session_id, test_id, user_id, len(question_ids),
        )

        return SessionOut(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=session.server_now,
            expires_at=session.expires_at,
            current_index=session.current_index,
            total_questions=len(question_ids),
            question=first_question,
        )

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: UUID,
        user_id: int,
        submitted_answers: list,
        idempotency_key: str,
    ) -> AnswerResult:
        """Score the current question, advance the state machine, finalize on
        the last question. Runs as a single transaction with a pessimistic lock
        on the session row.

        Concurrency model:
          * ``SELECT FOR UPDATE`` serializes concurrent submissions for the same
            session, so retries queue rather than double-score / double-advance.
          * the ``Idempotency-Key`` is checked *inside* the lock — a retry that
            arrives after the first commit sees the stored response and replays
            it without re-scoring.

        The per-question score/is_correct are persisted to ``answers`` but never
        returned (locked decision: no answer-key leakage mid-exam).
        """
        # 1. Acquire the pessimistic lock before reading current_index.
        session = await SessionRepository.get_for_update(db, session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.user_id != user_id:
            raise SessionForbiddenError("Session belongs to another user")

        # 2. Idempotency replay — return the stored response without re-scoring.
        existing = await IdempotencyRepository.get(db, session_id, idempotency_key)
        if existing is not None:
            logger.info(
                "answer idempotent replay: session_id=%s key=%s",
                session_id, idempotency_key,
            )
            return AnswerResult.model_validate(existing.response_body)

        # 3. State gate — terminal states are immutable.
        now = datetime.utcnow()
        if session.status != SessionStatus.ACTIVE:
            raise SessionTerminalError(f"Session is {session.status.value}")
        if session.expires_at is not None and session.expires_at < now:
            session.status = SessionStatus.EXPIRED
            await SessionRepository.flush(db, session)
            await db.commit()
            raise SessionExpiredError("Session has expired")

        # 4. Resolve the current question and score it server-side.
        question_ids = list(session.question_ids or [])
        idx = session.current_index
        if idx >= len(question_ids):
            # Past the last slot while still ACTIVE — defensive; treat as terminal.
            raise SessionTerminalError("No further questions to answer")

        qid = question_ids[idx]
        # NOTE (W3-F7 item 9b): this fetch runs while holding the FOR UPDATE
        # row lock. Blast radius is this session only (concurrent retries for
        # the same session queue here by design); worst-case hold time is the
        # client's bounded budget — 10s timeout × ≤3 attempts per fetch
        # (question_client._TIMEOUT / _MAX_RETRIES).
        question = await question_client.get_question(qid)
        result = scoring.score(
            question.get("type"),
            question.get("correct_answers"),
            submitted_answers,
        )

        await AnswerRepository.create(
            db,
            Answer(
                session_id=session_id,
                question_id=qid,
                question_index=idx,
                submitted_answers=submitted_answers,
                score=result.score,
                is_correct=result.is_correct,
            ),
        )

        # 5. Advance the state machine; finalize on the last question.
        session.current_index = idx + 1
        next_question = None
        if session.current_index >= len(question_ids):
            session.status = SessionStatus.SUBMITTED
            session.submitted_at = now
        else:
            nq = await question_client.get_question(
                question_ids[session.current_index]
            )
            next_question = _sanitize(nq)
        await SessionRepository.flush(db, session)

        out = AnswerResult(
            session_id=session_id,
            question_id=qid,
            current_index=session.current_index,
            total_questions=len(question_ids),
            status=session.status.value,
            submitted_at=session.submitted_at,
            next_question=next_question,
        )

        # 6. Store the dedup record (replayable) and commit the whole txn once.
        await IdempotencyRepository.create(
            db,
            IdempotencyKey(
                idempotency_key=idempotency_key,
                session_id=session_id,
                status_code=200,
                response_body=out.model_dump(mode="json"),
            ),
        )
        await db.commit()
        logger.info(
            "answer scored: session_id=%s q_index=%d status=%s",
            session_id, idx, session.status.value,
        )
        return out

    @staticmethod
    async def save_draft(
        db: AsyncSession,
        session_id: UUID,
        user_id: int,
        answers: dict,
    ) -> DraftSaveResult:
        """Persist an advisory autosave snapshot of in-progress answers (W3-F4).

        Last-write-wins: ``answers`` is stored verbatim on ``draft_answers`` and
        never scored. The session is **not** advanced — ``current_index`` and
        ``status`` are returned unchanged so the client can confirm autosave was
        non-mutating.

        State gate (semantic — the client must surface and halt, never retry):
          * 404 if the session is missing,
          * 403 if it belongs to another user,
          * 409 if the session is terminal (SUBMITTED/EXPIRED) or its
            ``expires_at`` has passed — you cannot autosave a finished exam.
        """
        session = await SessionRepository.get_by_id(db, session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.user_id != user_id:
            raise SessionForbiddenError("Session belongs to another user")

        now = datetime.utcnow()
        if session.status != SessionStatus.ACTIVE:
            raise SessionTerminalError(f"Session is {session.status.value}")
        if session.expires_at is not None and session.expires_at < now:
            session.status = SessionStatus.EXPIRED
            await SessionRepository.flush(db, session)
            await db.commit()
            raise SessionExpiredError("Session has expired")

        session.draft_answers = answers
        await SessionRepository.flush(db, session)
        await db.commit()
        logger.info(
            "draft saved: session_id=%s keys=%d index=%d (unchanged)",
            session_id, len(answers or {}), session.current_index,
        )
        return DraftSaveResult(
            session_id=session_id,
            status=session.status.value,
            current_index=session.current_index,
            saved_at=now,
        )
