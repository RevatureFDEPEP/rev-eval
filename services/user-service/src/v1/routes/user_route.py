"""
User Management Routes
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/users/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.get("/users/by-email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = UserService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with email: {email}")
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")
    return user


@router.get("/users/", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    return UserService.list_users(db=db, role=role, limit=limit, offset=offset)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")

    if user_update.email is not None:
        user.email = user_update.email
    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.commit()
    db.refresh(user)
    logger.info(f"Updated user: {user.email} (ID: {user.id})")
    return user


@router.post("/users/invite", response_model=InviteUserResponse, status_code=201)
def invite_user(invite_request: InviteUserRequest, db: Session = Depends(get_db)):
    try:
        result = UserService.invite_user(
            db=db,
            email=invite_request.email,
            first_name=invite_request.first_name,
            last_name=invite_request.last_name,
            role=invite_request.role,
        )
        return InviteUserResponse(**result)
    except Exception as e:
        logger.error(f"Error inviting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invite user: {str(e)}")
