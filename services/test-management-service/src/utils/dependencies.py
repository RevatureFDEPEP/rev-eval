"""
FastAPI dependencies for test-management-service.

The API Gateway verifies the JWT and injects X-User-* headers; this module
resolves those headers to a full user record by calling user-service.
"""
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, Header, HTTPException, status


def internal_auth_headers() -> Dict[str, str]:
    """Headers identifying this service as a trusted internal caller.

    Presents X-Internal-Key so user-service's admin-guarded read endpoints
    accept the server-to-server call. Empty when no key is configured.
    """
    key = os.getenv("INTERNAL_API_KEY")
    return {"X-Internal-Key": key} if key else {}


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
            response = await client.get(endpoint, headers=internal_auth_headers())
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


def role_of(user: Dict) -> str:
    """Normalized (upper-cased) role string for a resolved user dict."""
    return (user.get("role") or "").upper()


def is_admin(user: Dict) -> bool:
    return role_of(user) == "ADMIN"


def is_trainer(user: Dict) -> bool:
    return role_of(user) == "TRAINER"


async def get_current_trainer(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require the current user to have TRAINER role."""
    if not is_trainer(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role",
        )
    return current_user


async def get_current_trainer_or_admin(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require TRAINER or ADMIN. Used to guard management/write routes."""
    if not (is_trainer(current_user) or is_admin(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer or admin role",
        )
    return current_user


async def get_current_admin(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require ADMIN role."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin role",
        )
    return current_user


async def get_current_participant(
    current_user: Dict = Depends(get_current_user_from_headers),
) -> Dict:
    """Require the current user to have PARTICIPANT role."""
    if role_of(current_user) != "PARTICIPANT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires participant role",
        )
    return current_user


def ensure_can_access_submission(current_user: Dict, owner_user_id: Optional[int]) -> None:
    """Authorize access to a submission owned by `owner_user_id`.

    Participants may only touch their own submissions; trainers and admins may
    cross ownership boundaries (review/management workflows).
    """
    if is_trainer(current_user) or is_admin(current_user):
        return
    caller_id = current_user.get("id")
    if caller_id is None or owner_user_id is None or int(caller_id) != int(owner_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this submission",
        )
