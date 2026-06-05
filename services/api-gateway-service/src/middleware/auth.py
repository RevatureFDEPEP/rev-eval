"""
JWT authentication middleware for the API Gateway.

Verifies HS256 tokens issued by user-service, extracts the user context,
and injects it as X-User-* headers for downstream services.
"""
import os
from typing import Dict, Optional

import jwt
from fastapi import Cookie, Header, HTTPException, status

_JWT_SECRET_ENV = "JWT_SECRET"
_JWT_ALGORITHM_ENV = "JWT_ALGORITHM"
_DEFAULT_ALGORITHM = "HS256"
# Fallback when requests arrive via nginx directly (no BFF Bearer header).
_AUTH_COOKIE = "auth_token"


def _get_secret() -> str:
    secret = os.getenv(_JWT_SECRET_ENV)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{_JWT_SECRET_ENV} not configured",
        )
    return secret


async def verify_jwt_token(
    authorization: Optional[str] = Header(None),
    auth_token: Optional[str] = Cookie(None),
) -> Dict[str, str]:
    """Verify a JWT and return a user-context dict (user_id, email, role).

    Accepts a Bearer header (BFF path) or auth_token cookie (direct nginx path).
    """
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected: Bearer {token}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
    elif auth_token:
        token = auth_token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials: Authorization header or auth_token cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    algorithm = os.getenv(_JWT_ALGORITHM_ENV, _DEFAULT_ALGORITHM)

    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    return {
        "user_id": str(user_id),
        "email": payload.get("email", ""),
        "role": payload.get("role", ""),
    }


def add_user_context_headers(headers: dict, user_context: Dict[str, str]) -> dict:
    """Inject X-User-* headers for downstream services."""
    headers_copy = headers.copy()
    headers_copy["X-User-Id"] = str(user_context.get("user_id") or "")
    headers_copy["X-User-Email"] = str(user_context.get("email") or "")
    headers_copy["X-User-Role"] = str(user_context.get("role") or "")
    return headers_copy
