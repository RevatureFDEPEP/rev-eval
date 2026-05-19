"""
User Service

Business logic for user management (read/list/invite).
Authentication-specific logic lives in AuthService.
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return AuthService.get_user_by_id(db, user_id)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return AuthService.get_user_by_email(db, email)

    @staticmethod
    def list_users(
        db: Session,
        role: Optional[UserRole] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        return (
            query.order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def invite_user(
        db: Session,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.PARTICIPANT,
    ) -> Dict:
        """
        Create an inactive user record. Out-of-band credential delivery is
        the admin's responsibility (notification-service was removed for PEP).
        """
        existing = AuthService.get_user_by_email(db, email)
        if existing:
            return {
                "id": existing.id,
                "email": existing.email,
                "invite_sent": False,
                "message": "User already exists",
            }

        full_name = " ".join([p for p in [first_name, last_name] if p]) or None
        user = User(
            email=email,
            password_hash=None,
            first_name=first_name or "",
            last_name=last_name or "",
            full_name=full_name,
            role=role,
            is_active=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created invited user: {email} (ID: {user.id})")
        return {
            "id": user.id,
            "email": user.email,
            "invite_sent": False,
            "message": "User created (inactive). Deliver credentials out of band.",
        }
