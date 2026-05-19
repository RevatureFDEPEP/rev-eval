"""
User Management Routes

Endpoints for user management and synchronization with WorkOS.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import httpx
from src.db.session import get_db
from src.schemas.user_schema import UserOut, UserUpdate, InviteUserRequest, InviteUserResponse
from src.services.user_service import UserService
from src.models.user import UserRole
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WorkOS API
WORKOS_USER_API_URL = "https://api.workos.com/user_management/users/{user_id}"

router = APIRouter()


@router.post("/users/sync", response_model=UserOut)
async def sync_user_from_workos(
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_user_role: str = Header(..., alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    """
    Sync user from WorkOS JWT data.

    This endpoint is called by the API Gateway after JWT verification.
    It checks if the user exists in the database. If not, it fetches
    user details from WorkOS API and creates the user.

    Args:
        x_user_id: WorkOS user ID from X-User-Id header
        x_user_role: User role from X-User-Role header
        db: Database session

    Returns:
        User object
    """
    logger.info(f"📥 Syncing user from WorkOS: {x_user_id}")

    try:
        # Check if user already exists in database
        existing_user = UserService.get_user_by_workos_id(db, x_user_id)

        if existing_user:
            logger.info(f"✅ User already exists: {existing_user.email} (ID: {existing_user.id})")
            return existing_user

        # User not found - fetch from WorkOS API
        logger.info(f"👤 User not in database, fetching from WorkOS API...")

        api_key = os.getenv("WORKOS_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="WORKOS_API_KEY not configured"
            )

        user_url = WORKOS_USER_API_URL.format(user_id=x_user_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                user_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            user_data = response.json()

        # Extract user details from WorkOS API response
        email = user_data.get("email", "")
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")

        if not email:
            # Fallback: generate placeholder email if WorkOS doesn't have one
            email = f"workos_{x_user_id}@placeholder.revature.com"
            logger.warning(f"⚠️ No email in WorkOS response for {x_user_id}, using placeholder: {email}")

        logger.info(f"✅ Fetched from WorkOS: {email}")

        # Create user in database
        user = UserService.sync_user_from_workos(
            db=db,
            workos_id=x_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_string=x_user_role
        )

        logger.info(f"✅ User created successfully: {user.email} (ID: {user.id})")
        return user

    except httpx.HTTPError as e:
        logger.error(f"❌ Failed to fetch user from WorkOS: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user details from WorkOS: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error syncing user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync user: {str(e)}")


@router.get("/users/me", response_model=UserOut)
def get_current_user(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.

    This endpoint returns the user profile for the currently authenticated user
    based on the X-User-Id header set by the API Gateway after JWT verification.

    Args:
        x_user_id: WorkOS user ID from X-User-Id header
        db: Database session

    Returns:
        User object with full profile including database ID

    Raises:
        404: User not found
    """
    user = UserService.get_user_by_workos_id(db, x_user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with WorkOS ID: {x_user_id}")

    return user


@router.get("/users/{workos_id}", response_model=UserOut)
def get_user_by_workos_id(
    workos_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user by WorkOS ID.

    Args:
        workos_id: WorkOS user ID
        db: Database session

    Returns:
        User object

    Raises:
        404: User not found
    """
    user = UserService.get_user_by_workos_id(db, workos_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with WorkOS ID: {workos_id}")

    return user


@router.get("/users/by-email/{email}", response_model=UserOut)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Get user by email address.

    Args:
        email: User email
        db: Database session

    Returns:
        User object

    Raises:
        404: User not found
    """
    user = UserService.get_user_by_email(db, email)

    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with email: {email}")

    return user


@router.get("/users/", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    List users with optional filters.

    Args:
        role: Filter by role (TRAINER or PARTICIPANT)
        limit: Maximum number of results to return
        offset: Offset for pagination
        db: Database session

    Returns:
        List of User objects
    """
    users = UserService.list_users(
        db=db,
        role=role,
        limit=limit,
        offset=offset
    )

    return users


@router.patch("/users/{workos_id}", response_model=UserOut)
def update_user(
    workos_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user information.

    Args:
        workos_id: WorkOS user ID
        user_update: Fields to update
        db: Database session

    Returns:
        Updated User object

    Raises:
        404: User not found
    """
    user = UserService.get_user_by_workos_id(db, workos_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with WorkOS ID: {workos_id}")

    # Update fields
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name
    if user_update.role is not None:
        user.role = user_update.role

    db.commit()
    db.refresh(user)

    logger.info(f"✅ User updated: {user.email} (ID: {user.id})")
    return user


@router.post("/users/invite", response_model=InviteUserResponse, status_code=201)
def invite_user(
    invite_request: InviteUserRequest,
    db: Session = Depends(get_db)
):
    """
    Invite a new user to the platform.

    Creates a user record without WorkOS ID and sends a WorkOS invite.
    When the user signs in, their WorkOS ID will be linked to this record.

    Args:
        invite_request: Invitation details (email, optional name, role)
        db: Database session

    Returns:
        InviteUserResponse with user ID and invite status

    Raises:
        500: Error creating user or sending invite
    """
    try:
        result = UserService.invite_user(
            db=db,
            email=invite_request.email,
            first_name=invite_request.first_name,
            last_name=invite_request.last_name,
            role=invite_request.role
        )

        return InviteUserResponse(**result)

    except Exception as e:
        logger.error(f"❌ Error inviting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invite user: {str(e)}")
