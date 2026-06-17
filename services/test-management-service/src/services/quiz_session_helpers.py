"""Pure helpers for the quiz-session backend (W3-F1, Part B).

No I/O — no DB, no httpx, no clock side effects passed in explicitly — so these
are unit-testable with plain ``pytest`` (no async runner, no live Postgres/Mongo)
and the route/model/http-client modules stay out of the coverage denominator.

The route layer composes these: build the qms ``/sample`` query params, fan the
returned dicts through ``map_sample_to_question``, compute ``expires_at`` from
the test duration, and mint the opaque ``session_token``.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from src.schemas.quiz_session_schema import QuizQuestionOut

# Fallback session length when a test carries no explicit duration (1 hour).
DEFAULT_DURATION_SECONDS = 3600
# Token entropy: secrets.token_hex(32) -> 64 hex chars (256 bits).
SESSION_TOKEN_BYTES = 32
# Keep in sync with question-management-service's /questions/sample contract.
MAX_SAMPLE_QUERY_SIZE = 200


def build_sample_query(
    number_of_questions: int | None, skills: list[str] | None
) -> dict[str, str | int]:
    """Build the query params for the qms ``GET /v1/api/questions/sample`` call.

    Pure: returns a plain dict so the route's outbound request shape is asserted
    without httpx. ``n`` falls back to 20 when the test has no question count
    and is capped at qms's public maximum; ``skills`` is joined into the
    comma-separated string the qms endpoint parses, and omitted entirely when
    there are no skills (no empty ``skills=`` param).
    """
    n = number_of_questions if number_of_questions and number_of_questions > 0 else 20
    n = min(n, MAX_SAMPLE_QUERY_SIZE)
    params: dict[str, str | int] = {"n": n}
    if skills:
        cleaned = [s.strip() for s in skills if s and s.strip()]
        if cleaned:
            params["skills"] = ",".join(cleaned)
    return params


def resolve_duration_seconds(duration: timedelta | int | float | None) -> int:
    """Resolve a test duration to whole seconds, defaulting to one hour.

    Accepts a ``timedelta`` (the ORM ``Interval`` shape), a numeric seconds
    value, or ``None``. Non-positive/missing values fall back to the default.
    """
    if isinstance(duration, timedelta):
        seconds = int(duration.total_seconds())
    elif isinstance(duration, (int, float)):
        seconds = int(duration)
    else:
        seconds = DEFAULT_DURATION_SECONDS
    return seconds if seconds > 0 else DEFAULT_DURATION_SECONDS


def compute_expires_at(server_now: datetime, duration_seconds: int) -> datetime:
    """Server-authoritative expiry = ``server_now + duration``.

    Pure given an explicit ``server_now`` so the route stays the only place
    that reads the wall clock.
    """
    return server_now + timedelta(seconds=duration_seconds)


def mint_session_token() -> str:
    """Mint an opaque session bearer token (256 bits of entropy, hex-encoded)."""
    return secrets.token_hex(SESSION_TOKEN_BYTES)


def hash_session_token(raw: str) -> str:
    """Hash a raw session token for storage at rest (SHA-256 hex).

    The opaque token is returned to the client raw exactly once; only this
    SHA-256 digest is persisted, so a DB dump cannot be replayed as a bearer
    token. SHA-256 hex is 64 chars, matching the ``session_token_hash`` column
    width. (Plain SHA-256, not a slow KDF: the token is 256 bits of CSPRNG
    entropy, not a low-entropy human password, so it is not brute-forceable and
    needs no per-row salt.)
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def map_sample_to_question(doc: dict) -> QuizQuestionOut:
    """Map a qms-sampled question dict into the quiz-safe ``QuizQuestionOut``.

    The qms ``/sample`` projection already strips the answer key; this re-maps
    its field names (``_id`` -> ``question_id``, ``type`` -> ``question_type``)
    into the contract the frontend consumes, and never reads any answer field.
    """
    return QuizQuestionOut(
        question_id=str(doc.get("_id") or doc.get("question_id") or ""),
        question_text=doc.get("question_text") or "",
        question_type=doc.get("type") or doc.get("question_type") or "",
        difficulty=doc.get("difficulty") or "medium",
        options=doc.get("options"),
    )
