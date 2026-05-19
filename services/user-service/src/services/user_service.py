"""
User Service

Business logic for user management.
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.models.user import User, UserRole
from src.services.auth_service import AuthService
import os
import logging
from workos import WorkOSClient

logger = logging.getLogger(__name__)


# Initialize WorkOS client
def get_workos_client() -> Optional[WorkOSClient]:
    """Get WorkOS client if credentials are configured"""
    api_key = os.getenv("WORKOS_API_KEY")
    client_id = os.getenv("WORKOS_CLIENT_ID")
    if api_key and client_id:
        return WorkOSClient(api_key=api_key, client_id=client_id)
    return None


class UserService:
    @staticmethod
    def sync_user_from_workos(
        db: Session,
        workos_id: str,
        email: str,
        first_name: Optional[str],
        last_name: Optional[str],
        role_string: str
    ) -> User:
        """
        Sync user from WorkOS JWT data.

        Called by API Gateway after JWT verification.

        Args:
            db: Database session
            workos_id: WorkOS user ID from 'sub' claim
            email: User email
            first_name: User first name
            last_name: User last name
            role_string: Role string from JWT (e.g., 'trainer', 'org-participant')

        Returns:
            User object
        """
        # Map WorkOS role to application role
        role = AuthService.map_workos_role_to_app_role(role_string)

        # Get or create user
        user = AuthService.get_or_create_user(
            db=db,
            workos_id=workos_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        return user

    @staticmethod
    def get_user_by_workos_id(db: Session, workos_id: str) -> Optional[User]:
        """Get user by WorkOS ID"""
        return AuthService.get_user_by_workos_id(db, workos_id)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return AuthService.get_user_by_email(db, email)

    @staticmethod
    def list_users(
        db: Session,
        role: Optional[UserRole] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        List users with optional role filter.

        Args:
            db: Database session
            role: Filter by role (optional)
            limit: Max number of results
            offset: Offset for pagination

        Returns:
            List of User objects
        """
        query = db.query(User)

        if role:
            query = query.filter(User.role == role)

        query = query.order_by(User.created_at.desc())
        query = query.limit(limit).offset(offset)

        return query.all()

    @staticmethod
    def invite_user(
        db: Session,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.PARTICIPANT
    ) -> Dict:
        """
        Invite a new user.

        Creates a user record without WorkOS ID and sends WorkOS invite.
        When user signs in, the sync endpoint will update the record with WorkOS ID.

        Args:
            db: Database session
            email: User email
            first_name: User first name (optional)
            last_name: User last name (optional)
            role: User role (default: PARTICIPANT)

        Returns:
            Dict with user data and invite status
        """
        # Check if user already exists
        existing_user = AuthService.get_user_by_email(db, email)
        if existing_user:
            logger.info(f"User already exists: {email}")
            return {
                "id": existing_user.id,
                "email": existing_user.email,
                "invite_sent": False,
                "message": "User already exists"
            }

        # Create user without WorkOS ID
        user = User(
            workos_user_id=None,  # Will be set when user signs in
            email=email,
            first_name=first_name or "",
            last_name=last_name or "",
            role=role,
            is_active=False  # Inactive until they accept invite
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created user record for invite: {email} (ID: {user.id})")

        # Send WorkOS invite using SDK
        invite_sent = False
        invite_message = "User created, invite not configured"

        workos_client = get_workos_client()
        workos_org_id = os.getenv("WORKOS_DEFAULT_ORG")

        if workos_client and workos_org_id:
            try:
                # Send invitation using WorkOS SDK (uses default WorkOS invite URL)
                invitation = workos_client.user_management.send_invitation(
                    email=email,
                    organization_id=workos_org_id,
                    expires_in_days=7
                )

                invite_sent = True
                invite_message = f"Invite sent successfully. Invitation ID: {invitation.id}"
                logger.info(f"WorkOS invite sent to: {email} (Invitation ID: {invitation.id})")

            except Exception as e:
                invite_message = f"Error sending invite: {str(e)}"
                logger.error(f"Error sending WorkOS invite to {email}: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning("WorkOS credentials not configured, skipping invite")

        return {
            "id": user.id,
            "email": user.email,
            "invite_sent": invite_sent,
            "message": invite_message
        }
