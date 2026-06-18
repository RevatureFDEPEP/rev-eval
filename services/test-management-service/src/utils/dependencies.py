"""
FastAPI dependencies for test-management-service.

Two auth layers:
  1. verify_jwt / require_role  — service-level JWT decode (defense-in-depth;
     catches requests that bypass the gateway entirely).
  2. get_current_user_from_headers — gateway-injected X-User-* header lookup
     used when a full user record is needed (e.g. DB cross-reference).
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


async def get_current_user_from_headers(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """
    Resolve the authenticated user from gateway-supplied headers.

    Prefers X-User-Id (database PK) for lookup; falls back to X-User-Email
    when only the email header is present.
    """
    if not x_user_id and not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers (X-User-Id or X-User-Email)",
        )

    user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:8002")

    if x_user_id:
        endpoint = f"{user_service_url}/v1/api/users/{x_user_id}"
    else:
        endpoint = f"{user_service_url}/v1/api/users/by-email/{x_user_email}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to user-service: {e}",
        )

    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found in user-service",
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"user-service returned {response.status_code}",
    )


async def get_current_trainer(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require the current user to have TRAINER role."""
    if (current_user.get("role") or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role",
        )
    return current_user


async def get_current_participant(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require the current user to have PARTICIPANT role."""
    if (current_user.get("role") or "").upper() != "PARTICIPANT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires participant role",
        )
    return current_user
