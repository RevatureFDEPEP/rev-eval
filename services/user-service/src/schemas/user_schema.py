"""
User Schemas

Pydantic models for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    role: UserRole


class UserCreate(UserBase):
    """Schema for creating a new user (admin-side, with plaintext password)."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating user fields"""

    email: EmailStr | None = None
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    """Schema for user response"""

    id: int
    full_name: str | None
    is_active: bool
    organization_id: str | None
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True


class InviteUserRequest(BaseModel):
    """Schema for inviting a new user"""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole | None = UserRole.PARTICIPANT


class InviteUserResponse(BaseModel):
    """Schema for invite response"""

    id: int
    email: str
    invite_sent: bool
    message: str

    class Config:
        from_attributes = True
