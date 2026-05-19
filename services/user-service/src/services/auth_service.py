"""
Authentication Service for WorkOS Integration

Handles user synchronization from WorkOS authentication.
No password-based auth - all authentication handled by WorkOS.
"""
from typing import Optional
from sqlalchemy.orm import Session
from src.models.user import User, UserRole


class AuthService:
    @staticmethod
    def get_or_create_user(
        db: Session,
        workos_id: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.PARTICIPANT
    ) -> User:
        """
        Get or create a user from WorkOS authentication data.

        This is called after JWT verification by the API Gateway.
        It syncs user data from WorkOS into our local database.

        Args:
            db: Database session
            workos_id: WorkOS user ID from JWT 'sub' claim
            email: User email from JWT
            first_name: User first name from JWT
            last_name: User last name from JWT
            role: User role (TRAINER or PARTICIPANT)

        Returns:
            User object (created or updated)
        """
        # Try to find by WorkOS ID first (primary key for WorkOS users)
        user = db.query(User).filter(User.workos_user_id == workos_id).first()

        if user:
            # User exists - update info if changed
            updated = False

            if user.email != email:
                user.email = email
                updated = True

            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True

            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True

            # Update full_name if we have first/last name
            if first_name or last_name:
                full_name = f"{first_name or ''} {last_name or ''}".strip()
                if full_name and user.full_name != full_name:
                    user.full_name = full_name
                    updated = True

            if updated:
                db.commit()
                db.refresh(user)

            return user

        # Try to find by email (for existing users before WorkOS migration)
        user = db.query(User).filter(User.email == email).first()

        if user:
            # Link existing user with WorkOS ID (handles invited users)
            user.workos_user_id = workos_id
            user.is_active = True  # Activate user on first sign-in

            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name

            # Update full_name
            if first_name or last_name:
                user.full_name = f"{first_name or ''} {last_name or ''}".strip()

            db.commit()
            db.refresh(user)
            return user

        # Create new user
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        user = User(
            workos_user_id=workos_id,
            email=email,
            full_name=full_name if full_name else None,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_workos_id(db: Session, workos_id: str) -> Optional[User]:
        """Get user by WorkOS ID"""
        return db.query(User).filter(User.workos_user_id == workos_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def map_workos_role_to_app_role(workos_role: str) -> UserRole:
        """
        Map WorkOS organization role to application role.

        Args:
            workos_role: Role from WorkOS (e.g., 'org-trainer', 'trainer', 'org-participant')

        Returns:
            UserRole enum value (TRAINER or PARTICIPANT)
        """
        role_mapping = {
            "org-trainer": UserRole.TRAINER,
            "trainer": UserRole.TRAINER,
            "org-admin": UserRole.TRAINER,
            "admin": UserRole.TRAINER,
            "org-participant": UserRole.PARTICIPANT,
            "participant": UserRole.PARTICIPANT,
            "associate": UserRole.PARTICIPANT,
            "member": UserRole.PARTICIPANT,
        }

        return role_mapping.get(workos_role.lower(), UserRole.PARTICIPANT)
