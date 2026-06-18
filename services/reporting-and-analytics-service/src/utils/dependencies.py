"""
FastAPI auth dependencies for reporting-and-analytics-service.

Two layers (defense-in-depth):
  1. verify_jwt / require_role — service-level JWT decode; catches direct
     calls that bypass the API gateway.
  2. get_current_trainer / get_current_user — legacy header-based helpers
     kept for backward compatibility with tests that mock the gateway.
"""
import time
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer



from src.config.settings import settings

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# JWT layer (service-level, defense-in-depth)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Header layer (gateway-injected X-User-* headers)
# ---------------------------------------------------------------------------

def _parse_user_id(x_user_id: Optional[str]) -> int:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-User-Id header: must be numeric",
        )


async def get_current_trainer(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    user_id = _parse_user_id(x_user_id)
    if (x_user_role or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer role required",
        )
    return {"id": user_id, "role": x_user_role}


def get_current_user(
    payload: Dict = Depends(verify_jwt),
) -> Dict[str, Any]:
    """Extract identity from Bearer JWT — same token the trainer routes use."""
    user_id_str = payload.get("sub")
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sub claim in token",
        )
    return {"id": user_id, "role": (payload.get("role") or "").upper()}
