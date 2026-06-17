"""FastAPI dependencies for reporting-and-analytics-service.

The API gateway verifies the JWT and injects X-User-* headers; analytics is
restricted to trainer/admin callers. We gate on the gateway-verified role
header directly (no user-service round trip needed for read-only analytics).
This trusts the gateway boundary — the service is published on loopback only so
clients cannot bypass the gateway to spoof the role header.
"""
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status

_PRIVILEGED_ROLES = {"TRAINER", "ADMIN"}


async def get_user_context(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    if not x_user_id and not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers (X-User-Id or X-User-Email)",
        )
    return {
        "id": x_user_id,
        "email": x_user_email,
        "role": (x_user_role or "").upper(),
    }


async def require_trainer_or_admin(
    user: Dict[str, Any] = Depends(get_user_context),
) -> Dict[str, Any]:
    """Reject any non-trainer/admin caller — analytics is staff-only."""
    if user["role"] not in _PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reporting endpoints require trainer or admin role",
        )
    return user


def _same_user(user: Dict[str, Any], user_id: int) -> bool:
    """True when the caller's verified id matches the requested participant."""
    raw = user.get("id")
    if raw is None:
        return False
    try:
        return int(raw) == int(user_id)
    except (TypeError, ValueError):
        return False


async def require_self_or_privileged(
    user_id: int,
    user: Dict[str, Any] = Depends(get_user_context),
) -> Dict[str, Any]:
    """Authorize a candidate report read.

    Participants may read only their own report (``user_id`` must match the
    gateway-verified ``X-User-Id``). Trainers and admins may read any
    participant's report. Any other case is a 403 — we never confirm whether a
    different participant id exists.
    """
    if user["role"] in _PRIVILEGED_ROLES:
        return user
    if _same_user(user, user_id):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You may only read your own candidate report",
    )
