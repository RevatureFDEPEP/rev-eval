"""
FastAPI JWT auth dependencies for question-management-service.

verify_jwt   — decodes Bearer token directly (defense-in-depth).
require_role — factory that composes verify_jwt + role check.
get_caller   — resolves who is calling a read endpoint: test-management-service
               (shared internal token) or a user (verified Bearer JWT).

Every endpoint requires a caller. Write endpoints and image upload require the
TRAINER role. Read endpoints accept any authenticated user, but answer keys are
returned only to trainers and to test-management-service, which needs them for
scoring; participants receive questions without them.
"""
import hmac
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.settings import settings

_bearer = HTTPBearer(auto_error=False)

INTERNAL_TOKEN_HEADER = "X-Internal-Service-Token"


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


@dataclass(frozen=True)
class Caller:
    """Who is calling a read endpoint."""
    role: str
    internal: bool = False

    @property
    def can_see_answers(self) -> bool:
        return self.internal or self.role.upper() == "TRAINER"


def _is_internal(token: Optional[str]) -> bool:
    expected = settings.INTERNAL_SERVICE_TOKEN
    if not expected or not token:
        return False
    return hmac.compare_digest(token.encode(), expected.encode())


def get_caller(
    internal_token: Optional[str] = Header(None, alias=INTERNAL_TOKEN_HEADER),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Caller:
    """Resolve the caller. A wrong or missing internal token is ignored, and the
    request is then authenticated as a user like any other."""
    if _is_internal(internal_token):
        return Caller(role="SERVICE", internal=True)
    payload = verify_jwt(credentials)
    return Caller(role=(payload.get("role") or "").upper())
