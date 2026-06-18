"""
Session service for test-management-service.

Responsibilities:
- Validate the requested test exists and extract its duration.
- Sample question IDs from question-management-service via $sample aggregation.
- Generate server-authoritative session_id, session_token, server_now, expires_at.
- Persist the session row (including ordered question_ids) before responding.
- Propagate X-Correlation-Id to all outbound httpx calls.
- Score submitted answers and advance the session state.
"""
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.session_answer_repository import SessionAnswerRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.session_schema import AnswerResponse, SessionStartResponse
from src.scoring import exact_match, partial_credit
from src.utils.http_client import get_http_client

_QUESTION_SERVICE_URL = os.getenv("QUESTION_SERVICE_URL", "http://question-management-service:8003")
_DEFAULT_DURATION_SECONDS = 7200  # 2-hour fallback when test.duration is not set

# Question types that receive Jaccard partial-credit scoring
_PARTIAL_CREDIT_TYPES = {
    "multiple_select", "multi_select", "checkbox", "multi_answer",
    "text", "short_answer", "essay", "fill_in_the_blank",
}


class SessionService:

    @staticmethod
    async def start_session(
        db: AsyncSession,
        test_id: int,
        user_id: int,
        correlation_id: Optional[str] = None,
    ) -> SessionStartResponse:
        """
        Create a new quiz session.

        1. Fetch the test (validates existence + gets duration).
        2. Sample question IDs from question-management-service.
        3. Fetch first question body.
        4. Persist the session row (including question_ids).
        5. Return the response — the client never computes timing state.
        """
        # ── 1. Resolve test ──────────────────────────────────────────────────
        test = await TestRepository.get_by_id(db, test_id)
        if test is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found",
            )

        question_count: int = test.number_of_questions or 20
        duration_seconds: int = (
            int(test.duration.total_seconds()) if test.duration else _DEFAULT_DURATION_SECONDS
        )

        # ── 2. Sample questions from question-management-service ─────────────
        outbound_headers: Dict[str, str] = {}
        if correlation_id:
            outbound_headers["X-Correlation-Id"] = correlation_id

        client: httpx.AsyncClient = get_http_client()
        try:
            sample_resp = await client.get(
                f"{_QUESTION_SERVICE_URL}/v1/api/questions/random",
                params={"count": question_count},
                headers=outbound_headers,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach question-management-service: {exc}",
            )

        if sample_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"question-management-service returned {sample_resp.status_code}",
            )

        sampled_questions: list = sample_resp.json()
        question_ids: List[str] = [q["_id"] for q in sampled_questions if "_id" in q]

        # Strip correct_answers so they never leave the server boundary
        questions: list[Dict[str, Any]] = [
            {k: v for k, v in q.items() if k != "correct_answers"}
            for q in sampled_questions
        ]
        first_question: Optional[Dict[str, Any]] = questions[0] if questions else None

        # ── 3. Build server-authoritative timing ────────────────────────────
        server_now = datetime.utcnow()
        expires_at = server_now + timedelta(seconds=duration_seconds)
        session_id = str(uuid.uuid4())
        session_token = secrets.token_hex(32)  # 64-char hex string

        # ── 5. Persist (including the ordered question list) ─────────────────
        await SessionRepository.create(
            db,
            session_id=session_id,
            test_id=test_id,
            user_id=user_id,
            session_token=session_token,
            server_now=server_now,
            expires_at=expires_at,
            question_ids=question_ids,
        )

        return SessionStartResponse(
            session_id=session_id,
            session_token=session_token,
            server_now=server_now,
            expires_at=expires_at,
            first_question=first_question,
            questions=questions,
        )

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: str,
        submitted_answers: List[Any],
        idempotency_key: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> AnswerResponse:
        """
        Score the answer for the current question and advance the session.

        Steps:
        1. Acquire SELECT FOR UPDATE lock on the session row.
        2. Guard: session must be ACTIVE and not expired.
        3. Check idempotency key — return cached response if already seen.
        4. Fetch current question from question-management-service.
        5. Score using the appropriate scorer (exact_match or partial_credit).
        6. Persist the answer record (within the same transaction).
        7. Advance current_index; if last question, mark SUBMITTED.
        8. Store idempotency response and commit.
        9. Optionally fetch next question and return AnswerResponse.
        """
        from src.models.session import SessionStatus  # local import avoids circulars

        # ── 1. Lock session row ──────────────────────────────────────────────
        session = await SessionRepository.get_locked(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # ── 2. Guard: must be ACTIVE ─────────────────────────────────────────
        if session.status == SessionStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session is already submitted; no further answers accepted",
            )
        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session is {session.status.value} and cannot accept answers",
            )
        if datetime.utcnow() > session.expires_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has expired",
            )

        question_ids: List[str] = session.question_ids or []
        if not question_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Session has no questions assigned",
            )

        current_idx = session.current_index
        if current_idx >= len(question_ids):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="All questions have already been answered",
            )

        current_question_id = question_ids[current_idx]

        # ── 3. Idempotency check ─────────────────────────────────────────────
        if idempotency_key:
            existing = await IdempotencyRepository.get(
                db, idempotency_key=idempotency_key, session_id=session_id
            )
            if existing:
                return AnswerResponse(**json.loads(existing.response_body))

        # ── 4. Fetch current question ────────────────────────────────────────
        outbound_headers: Dict[str, str] = {}
        if correlation_id:
            outbound_headers["X-Correlation-Id"] = correlation_id

        client: httpx.AsyncClient = get_http_client()
        question_data: Optional[Dict[str, Any]] = None
        try:
            q_resp = await client.get(
                f"{_QUESTION_SERVICE_URL}/v1/api/questions/{current_question_id}",
                headers=outbound_headers,
            )
            if q_resp.status_code == 200:
                question_data = q_resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach question-management-service: {exc}",
            )

        if question_data is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not fetch question {current_question_id}",
            )

        question_type: str = question_data.get("type") or question_data.get("question_type") or "mcq"
        correct_answers: List[Any] = question_data.get("correct_answers") or question_data.get("answers") or []

        # ── 5. Score ─────────────────────────────────────────────────────────
        # AI-assisted (Claude Code): the scorer-selection rule was drafted with
        # AI. Human review chose to key the decision off a single
        # `_PARTIAL_CREDIT_TYPES` set so the policy lives in one place, and
        # confirmed multi-select falls through to `exact_match` (full-match) per
        # ADR 0002 rather than receiving Jaccard partial credit.
        scorer = (
            partial_credit
            if question_type.lower() in _PARTIAL_CREDIT_TYPES
            else exact_match
        )
        result = scorer.score_question(question_type, correct_answers, submitted_answers)

        # ── 6. Persist answer (flush within transaction) ─────────────────────
        await SessionAnswerRepository.create(
            db,
            session_id=session_id,
            question_id=current_question_id,
            submitted_answers=submitted_answers,
            score=result.score,
            is_correct=result.is_correct,
        )

        # ── 7. Advance index and check completion ────────────────────────────
        new_index = current_idx + 1
        is_last = new_index >= len(question_ids)
        await SessionRepository.advance_index(
            db, session, new_index=new_index, submitted=is_last
        )

        # ── 8. Build response (before commit so we read dirty state) ─────────
        response = AnswerResponse(
            session_id=session_id,
            question_id=current_question_id,
            score=result.score,
            is_correct=result.is_correct,
            points_earned=result.points_earned,
            points_possible=result.points_possible,
            details=result.details,
            current_index=session.current_index,
            session_status=session.status,
            next_question=None,
            submitted_at=session.submitted_at,
        )

        # ── 9. Store idempotency key (still inside the same transaction) ─────
        if idempotency_key:
            cache_payload = response.model_dump(mode="json")
            await IdempotencyRepository.create(
                db,
                idempotency_key=idempotency_key,
                session_id=session_id,
                response_body=json.dumps(cache_payload),
            )

        # ── 10. Single atomic commit: answer + index + idempotency key ───────
        await db.commit()
        await db.refresh(session)

        # ── 11. Fetch next question (non-fatal, after commit) ────────────────
        if not is_last:
            next_id = question_ids[new_index]
            try:
                nq_resp = await client.get(
                    f"{_QUESTION_SERVICE_URL}/v1/api/questions/{next_id}",
                    headers=outbound_headers,
                )
                if nq_resp.status_code == 200:
                    response.next_question = nq_resp.json()
            except httpx.RequestError:
                pass

        return response
