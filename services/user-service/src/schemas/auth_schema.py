from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class StudentLoginRequest(BaseModel):
    email: EmailStr
    password: str

class StudentRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class TrainerEmailRequest(BaseModel):
    email: EmailStr

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
