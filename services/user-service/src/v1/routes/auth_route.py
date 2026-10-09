from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.user import User, UserRole
from src.schemas.auth_schema import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from src.services.auth_service import AuthService
from src.utils.dependencies import get_current_user

router = APIRouter(tags=["Authentication"])


def _issue_token(user: User) -> str:
    return AuthService.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Self-registration is unauthenticated, so it can never grant privilege:
    # it always creates a PARTICIPANT. Trainer accounts are provisioned through
    # a trusted path (the seed script or a direct database insert).
    if request.role is not None and request.role != UserRole.PARTICIPANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration creates participant accounts only",
        )
    if AuthService.get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = AuthService.create_user(
        db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        role=UserRole.PARTICIPANT,
    )
    return AuthResponse(
        access_token=_issue_token(user),
        user=UserResponse.model_validate(user),
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return AuthResponse(
        access_token=_issue_token(user),
        user=UserResponse.model_validate(user),
    )


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
