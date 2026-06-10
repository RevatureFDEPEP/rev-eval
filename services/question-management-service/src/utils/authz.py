"""Role-based guards for answer-key-bearing endpoints (W3-F7 item 4).

Kept separate from the route module so the guard logic is unit-testable
without importing the full router (and its service/upload dependencies).
"""
from typing import Optional

from fastapi import Header, HTTPException, status

# Roles allowed to read endpoints that return full documents including the
# answer key (correct_answers / sample_answer).
_ANSWER_KEY_ROLES = {"TRAINER", "ADMIN"}


async def require_answer_key_role(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> None:
    """Role gate for bulk answer-key reads (W3-F7 item 4).

    The gateway overwrites ``X-User-Role`` from the verified JWT on every
    authenticated request, so browser traffic always carries the caller's
    real role — a participant cannot spoof it through the gateway. An ABSENT
    header means an internal service-to-service call inside the compose
    network (test-management-service's session sampler sends only
    ``X-Correlation-Id``), which is allowed per the platform's
    trust-the-gateway model.

    NOTE: ``GET /questions`` and ``GET /questions/{id}`` share this leak
    class; the full API-layer RBAC sweep is deferred to W4-F3.
    """
    if x_user_role is not None and x_user_role not in _ANSWER_KEY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to sample the question bank",
        )
