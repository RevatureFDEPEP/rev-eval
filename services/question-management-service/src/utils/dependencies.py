"""
FastAPI dependencies for question-management-service.

The API Gateway is the security boundary: it verifies the JWT and injects
``X-User-*`` headers before the request reaches this service. We therefore
trust the injected ``X-User-Role`` header directly for authorization, with no
round-trip back to user-service.
"""
from fastapi import Header, HTTPException, status


async def require_trainer(
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> str:
    """Require the gateway-injected role to be TRAINER.

    Returns the normalized role on success; raises 401 when the header is
    missing (request did not pass the gateway) and 403 when the caller is
    authenticated but not a trainer.
    """
    if not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication header (X-User-Role)",
        )
    if x_user_role.upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role",
        )
    return x_user_role.upper()
