from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.schemas.auth_schema import (
    StudentLoginRequest,
    StudentRegisterRequest,
    TrainerEmailRequest,
    AuthResponse,
    UserResponse
)
from src.services.auth_service import AuthService
from src.db.session import get_db
from src.models.user import UserRole

router = APIRouter(tags=["Authentication"])

@router.post("/auth/student/login", response_model=AuthResponse)
def student_login(request: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate student with email and password
    """
    user = AuthService.authenticate_student(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Create access token
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role.value}
    )

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/auth/student/register", response_model=AuthResponse)
def student_register(request: StudentRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new student
    """
    # Check if user already exists
    existing_user = AuthService.get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new student
    user = AuthService.create_student(
        db,
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )

    # Create access token
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role.value}
    )

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/auth/trainer/verify-email")
def verify_trainer_email(request: TrainerEmailRequest):
    """
    Verify if email ends with @revature.com for trainer authentication
    Returns whether the email is valid for WorkOS SSO
    """
    is_valid_trainer = request.email.endswith("@revature.com")
    return {
        "is_valid_trainer": is_valid_trainer,
        "email": request.email
    }

@router.get("/auth/me", response_model=UserResponse)
def get_current_user(
    # TODO: Add JWT token dependency here
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user
    """
    # This is a placeholder - you'll need to implement JWT token verification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="JWT verification not implemented yet"
    )
