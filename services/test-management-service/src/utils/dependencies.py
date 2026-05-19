"""
FastAPI Dependencies

Provides reusable dependency functions for routes.
"""
from typing import Optional, Dict
from fastapi import Header, HTTPException, status, Depends
import httpx
import os


async def get_current_user_from_headers(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_first_name: Optional[str] = Header(None, alias="X-User-First-Name"),
    x_user_last_name: Optional[str] = Header(None, alias="X-User-Last-Name"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, any]:
    """
    Extract user context from headers (set by API Gateway) and fetch user from user-service.

    This dependency:
    1. Extracts user information from headers set by the API Gateway
    2. Calls user-service to get or create the user in the database
    3. Returns the user data dict for use in route handlers

    Args:
        x_user_id: WorkOS user ID from X-User-Id header
        x_user_email: User email from X-User-Email header
        x_user_first_name: User first name from X-User-First-Name header
        x_user_last_name: User last name from X-User-Last-Name header
        x_user_role: User role from X-User-Role header

    Returns:
        User data dict with keys: id, email, workos_id, role, etc.

    Raises:
        HTTPException: If required headers are missing or user-service call fails
    """
    if not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-User-Email"
        )

    # Direct service-to-service communication (internal network)
    # API Gateway already synced the user, so this should always succeed
    user_service_url = os.getenv("USER_SERVICE_URL", "http://localhost:8003")

    try:
        # Call user-service directly (internal service communication)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{user_service_url}/v1/api/users/by-email/{x_user_email}"
            )

            if response.status_code == 200:
                user_data = response.json()
                return user_data
            elif response.status_code == 404:
                # User doesn't exist, shouldn't happen if API Gateway sync worked
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"User not found in database: {x_user_email}. User sync may have failed."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch user from user-service: {response.status_code}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to user-service: {str(e)}"
        )


async def get_current_trainer(
    current_user: Dict = Depends(get_current_user_from_headers)
) -> Dict:
    """
    Dependency that ensures the current user is a trainer.

    Args:
        current_user: Current authenticated user data dict

    Returns:
        User data dict if user is a trainer

    Raises:
        HTTPException: If user is not a trainer
    """
    user_role = current_user.get("role", "").upper()
    if user_role != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires trainer role"
        )
    return current_user


async def get_current_participant(
    current_user: Dict = Depends(get_current_user_from_headers)
) -> Dict:
    """
    Dependency that ensures the current user is a participant.

    Args:
        current_user: Current authenticated user data dict

    Returns:
        User data dict if user is a participant

    Raises:
        HTTPException: If user is not a participant
    """
    user_role = current_user.get("role", "").upper()
    if user_role != "PARTICIPANT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires participant role"
        )
    return current_user
