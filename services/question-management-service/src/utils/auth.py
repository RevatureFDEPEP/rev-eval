"""
Authorization dependencies for question-management-service.

KNOWN HEADER-TRUST GAP (defense-in-depth caveat)
-------------------------------------------------
This service does NOT have a verified-JWT auth layer of its own. In the
rev-eval topology the API Gateway
(`services/api-gateway-service/src/middleware/auth.py`) verifies the Bearer
JWT (signature + expiry + `algorithms=["HS256"]`) and injects the
`X-User-Id` / `X-User-Email` / `X-User-Role` context headers. Downstream
services — including this one — currently *trust* those headers without
re-verifying the JWT.

That means a caller who reaches this service directly (bypassing the gateway,
e.g. `curl` on the internal network) can forge `X-User-Role: TRAINER`. The
PEP-recommended posture is for each service to independently verify the JWT;
until that exists, the only real control is network lockdown at the gateway.

This module mirrors test-management-service's role-gate *shape*
(`get_current_trainer` -> 403 on role mismatch, 401 on missing identity) but
reads the role from the gateway header rather than calling user-service,
because qms has no user-service client wired in. The role is still read from
a server-injected header and never from the request body or query string.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, status


async def get_current_user_from_headers(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> dict[str, Any]:
    """
    Resolve the caller's identity from gateway-injected context headers.

    401 when no identifying header is present (unknown identity). The role is
    taken verbatim from `X-User-Role` (see module-level header-trust caveat).
    """
    if not x_user_id and not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers (X-User-Id or X-User-Email)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": x_user_id,
        "email": x_user_email,
        "role": x_user_role,
    }


async def get_current_trainer(
    current_user: dict = Depends(get_current_user_from_headers),
) -> dict:
    """Require the resolved caller to have the TRAINER role (403 otherwise)."""
    if (current_user.get("role") or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role",
        )
    return current_user
