"""
Authentication service: bcrypt password hashing + JWT (HS256) issuance and verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.user import User, UserRole


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(plain: str) -> str:
        return pwd_context.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        if not hashed:
            return False
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> dict:
        """Decode and verify JWT; raises jwt.PyJWTError on failure."""
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        user = AuthService.get_user_by_email(db, email)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not AuthService.verify_password(password, user.password_hash or ""):
            return None
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.PARTICIPANT,
    ) -> User:
        first_name = None
        last_name = None
        if full_name:
            parts = full_name.strip().split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else None

        user = User(
            email=email,
            password_hash=AuthService.hash_password(password),
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # Backwards-compatible aliases used by the existing auth_route scaffolding.
    @staticmethod
    def authenticate_student(db: Session, email: str, password: str) -> Optional[User]:
        return AuthService.authenticate_user(db, email, password)

    @staticmethod
    def create_student(
        db: Session, email: str, password: str, full_name: Optional[str] = None
    ) -> User:
        return AuthService.create_user(db, email, password, full_name, UserRole.PARTICIPANT)
