"""
FastAPI JWT auth dependencies for question-management-service.

verify_jwt  — decodes Bearer token directly (defense-in-depth).
require_role — factory that composes verify_jwt + role check.

Write endpoints (create / update / delete) require TRAINER role.
Read endpoints remain open (any authenticated call via the gateway).
"""
import time
from typing import Any, Callable, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.settings import settings

_bearer = HTTPBearer(auto_error=False)


def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    """Decode and validate Bearer JWT. Raises 401 if missing / invalid / expired."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload["exp"] < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    return payload


def require_role(role: str) -> Callable:
    """Factory: returns a FastAPI dependency that enforces a specific JWT role."""
    def _dependency(payload: Dict = Depends(verify_jwt)) -> Dict:
        if (payload.get("role") or "").upper() != role.upper():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{role.capitalize()} role required",
            )
        return payload
    return _dependency
