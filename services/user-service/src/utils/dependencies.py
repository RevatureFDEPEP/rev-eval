"""FastAPI dependencies for the user-service."""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.db.session import get_db
from src.models.user import User, UserRole
from src.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=True)
# auto_error=False so internal-key callers without a Bearer token are allowed
# to reach the dependency body instead of being rejected by the scheme.
optional_bearer_scheme = HTTPBearer(auto_error=False)

INTERNAL_KEY_HEADER = "X-Internal-Key"


def is_admin(user: User) -> bool:
    """True when the user holds the ADMIN role."""
    return user.role == UserRole.ADMIN


def _internal_key_ok(provided: Optional[str]) -> bool:
    """True when a configured internal key is presented and matches.

    Disabled (always False) when INTERNAL_API_KEY is unset, so the bypass can
    never be triggered by an empty/missing configuration.
    """
    configured = settings.INTERNAL_API_KEY
    return bool(configured) and provided == configured


def _resolve_user_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> Optional[User]:
    """Decode a Bearer token to a User, or None when no credentials supplied.

    Raises 401 when a token is present but invalid/expired or the user is gone.
    """
    if credentials is None:
        return None

    try:
        payload = AuthService.decode_access_token(credentials.credentials)
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    user = AuthService.get_user_by_id(db, int(sub))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""
    return _resolve_user_from_credentials(credentials, db)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Resolve the user from a Bearer JWT if present, else None (no error)."""
    return _resolve_user_from_credentials(credentials, db)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have the ADMIN role."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_current_admin_or_self(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    """Allow access when the caller is the target user or an ADMIN.

    `user_id` is bound from the matching path parameter; the caller must be
    acting on their own record or hold the ADMIN role.
    """
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own profile unless you are an admin",
        )
    return current_user


def get_admin_or_internal(
    x_internal_key: Optional[str] = Header(None, alias=INTERNAL_KEY_HEADER),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Optional[User]:
    """Admin JWT, or a trusted internal service key.

    Internal calls (test-management resolving a user) present X-Internal-Key
    and carry no token; returns None for those. External callers must be admin.
    """
    if _internal_key_ok(x_internal_key):
        return current_user
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_admin_or_self_or_internal(
    user_id: int,
    x_internal_key: Optional[str] = Header(None, alias=INTERNAL_KEY_HEADER),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Optional[User]:
    """Trusted internal key, the target user, or an ADMIN may read the record."""
    if _internal_key_ok(x_internal_key):
        return current_user
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own profile unless you are an admin",
        )
    return current_user
