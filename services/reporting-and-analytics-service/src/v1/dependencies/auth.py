"""JWT role-gate dependencies for trainer-only reporting endpoints.

Defense-in-depth (W4-F3): platform-wide, the API gateway is the auth boundary
and downstream services trust its X-User-* headers. This module deliberately
breaks that pattern for trainer-level data — it re-verifies the Authorization
JWT with the shared signing key, so a caller who bypasses the gateway (curl
straight to :8004 with spoofed X-User-Role headers) is still rejected. The
role claim is read ONLY from the verified token payload, never from request
headers or body.

AI-assisted (Claude Code); human-reviewed authorization gate — see
docs/ai-assistance.md.
"""
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from src.config.settings import settings

TRAINER_ROLE = "TRAINER"


def require_trainer(authorization: str | None = Header(None)) -> dict:
    """Allow only callers presenting a valid JWT whose role claim is TRAINER.

    401 — missing/malformed Authorization header, bad signature, expired exp
    403 — token verified, but role != TRAINER
    Returns the verified claims dict.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        # `from None`: the jose internals are noise to an API caller (B904).
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    if payload.get("role") != TRAINER_ROLE:
        raise HTTPException(status_code=403, detail="Trainer role required")
    return payload
