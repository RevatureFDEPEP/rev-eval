"""FastAPI dependencies for question-management-service.

This service trusts the gateway-injected X-User-Role header (the gateway
verifies the JWT and strips any client-supplied identity headers). Write
routes require a privileged role; reads remain open with answer-key gating
handled in the routes.
"""
from typing import Optional

from fastapi import Header, HTTPException, status

_EDITOR_ROLES = {"TRAINER", "ADMIN"}


def require_question_editor(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> str:
    """Require a trainer/admin role to mutate questions.

    401 when no role is present (unauthenticated / role-less token); 403 when
    the caller is authenticated but lacks edit privileges.
    """
    role = (x_user_role or "").strip().upper()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    if role not in _EDITOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer or admin role",
        )
    return role
