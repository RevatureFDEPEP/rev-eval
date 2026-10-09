"""
User Management Routes

Every route resolves the caller from the signed Bearer JWT (get_current_user),
never from forwarded X-User-* headers. Unauthenticated -> 401, forbidden -> 403.

Policy (roles are TRAINER and PARTICIPANT; there is no admin role):
- /users/me: any authenticated, active user.
- GET /users/{id}, GET /users/by-email/{email}: the caller's own record, or any
  record for a TRAINER (trainers resolve participants when assigning tests and
  reviewing submissions).
- GET /users/: TRAINER only.
- POST /users/invite: TRAINER only, and only PARTICIPANT accounts (test
  assignment invites participants; nothing in the product invites trainers).
- PATCH /users/{id}: the caller's own first_name / last_name only. Email, role
  and is_active are not changeable through this API by anyone, and no caller
  may patch another user; no product workflow does either.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.user import User, UserRole
from src.schemas.user_schema import (
    InviteUserRequest,
    InviteUserResponse,
    UserOut,
    UserUpdate,
)
from src.services.user_service import UserService
from src.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_trainer(user: User) -> bool:
    return user.role == UserRole.TRAINER


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@router.get("/users/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.get("/users/by-email/{email}", response_model=UserOut)
def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_trainer(current_user) and email.strip().lower() != (current_user.email or "").lower():
        raise _forbidden("You can only look up your own account")
    user = UserService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with email: {email}")
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_trainer(current_user) and user_id != current_user.id:
        raise _forbidden("You can only read your own account")
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")
    return user


@router.get("/users/", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_trainer(current_user):
        raise _forbidden("Trainer role required")
    return UserService.list_users(db=db, role=role, limit=limit, offset=offset)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Authorization is decided before the lookup, so a forbidden caller cannot
    # probe which ids exist.
    if user_id != current_user.id:
        raise _forbidden("You can only update your own account")
    if user_update.role is not None or user_update.is_active is not None:
        raise _forbidden("Role and active status cannot be changed through this API")
    if user_update.email is not None:
        raise _forbidden("Email cannot be changed through this API")

    user = UserService.get_user_by_id(db, user_id)
    if not user:  # pragma: no cover - the caller was just resolved from this id
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")

    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name

    db.commit()
    db.refresh(user)
    logger.info(f"Updated user: {user.email} (ID: {user.id})")
    return user


@router.post("/users/invite", response_model=InviteUserResponse, status_code=201)
def invite_user(
    invite_request: InviteUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_trainer(current_user):
        raise _forbidden("Trainer role required")
    if invite_request.role not in (None, UserRole.PARTICIPANT):
        raise _forbidden("Only participant accounts can be invited")
    try:
        result = UserService.invite_user(
            db=db,
            email=invite_request.email,
            first_name=invite_request.first_name,
            last_name=invite_request.last_name,
            role=UserRole.PARTICIPANT,
        )
        return InviteUserResponse(**result)
    except Exception as e:
        logger.error(f"Error inviting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invite user: {str(e)}")
