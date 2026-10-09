"""
FastAPI dependencies for test-management-service.

Identity comes only from the caller's own Bearer JWT:
  1. verify_jwt checks the signature and expiry here, so a request that skips
     the gateway (for example on a published development port) is still
     authenticated.
  2. get_current_user loads the token subject's record from user-service,
     forwarding the same token, so the role is the stored one and inactive
     users are refused. X-User-* headers are never trusted for identity.

get_current_trainer / get_current_participant add the role requirement.
Record-level rules (which test, submission or session) live in
src/utils/authorization.py.
"""
import os
import time
from typing import Any, Callable, Dict, Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
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


def user_service_headers(authorization: Optional[str]) -> Dict[str, str]:
    """Headers that carry the caller's own Bearer token to user-service."""
    if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
        return {"Authorization": authorization}
    return {}


async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_jwt),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    Resolve the caller from their verified Bearer JWT.

    The token subject is looked up in user-service with the caller's own token,
    which user-service verifies again; a missing or inactive user is a 401.
    """
    subject = str(payload["sub"])
    user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:8002")
    endpoint = f"{user_service_url}/v1/api/users/{subject}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint, headers=user_service_headers(authorization))
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to user-service: {e}",
        )

    if response.status_code == 200:
        user = response.json()
        if str(user.get("id")) != subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="user-service returned a different user than the token subject",
            )
        return user
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found in user-service",
        )
    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user-service did not accept the caller's credentials",
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"user-service returned {response.status_code}",
    )


async def get_current_trainer(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Require the current user to have TRAINER role."""
    if (current_user.get("role") or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role",
        )
    return current_user


async def get_current_participant(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Require the current user to have PARTICIPANT role."""
    if (current_user.get("role") or "").upper() != "PARTICIPANT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires participant role",
        )
    return current_user
