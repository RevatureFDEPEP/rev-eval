"""
User Schemas

Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from src.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: UserRole


class UserCreate(UserBase):
    """Schema for creating a new user (admin-side, with plaintext password)."""
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating user fields"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    """Schema for user response"""
    id: int
    full_name: Optional[str]
    is_active: bool
    organization_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class InviteUserRequest(BaseModel):
    """Schema for inviting a new user"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.PARTICIPANT


class InviteUserResponse(BaseModel):
    """Schema for invite response"""
    id: int
    email: str
    invite_sent: bool
    message: str

    class Config:
        from_attributes = True
