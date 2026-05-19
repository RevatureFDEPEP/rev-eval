"""
Email Schemas

Pydantic schemas for email-related requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SendEmailRequest(BaseModel):
    """Request schema for sending a generic email"""
    recipient_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    html_content: str = Field(..., min_length=1)
    text_content: Optional[str] = None
    template_name: Optional[str] = None


class SendTemplatedEmailRequest(BaseModel):
    """Request schema for sending a templated email"""
    recipient_email: EmailStr
    template_name: str = Field(..., min_length=1, max_length=100)
    context: Dict[str, Any] = Field(default_factory=dict)


class InviteUserEmailRequest(BaseModel):
    """Request schema for sending user invitation email"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    invite_token: str = Field(..., min_length=1)


class TestAssignmentEmailRequest(BaseModel):
    """Request schema for sending test assignment email"""
    participant_email: EmailStr
    test_id: int
    test_name: str
    role: str
    curriculum: str
    skills: list[str]
    duration_minutes: int
    deadline: Optional[str] = None


class EmailResponse(BaseModel):
    """Response schema for email sending"""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    log_id: Optional[int] = None


class EmailLogResponse(BaseModel):
    """Response schema for email log entry"""
    id: int
    recipient_email: str
    subject: str
    template_name: Optional[str]
    status: str
    ses_message_id: Optional[str]
    error_message: Optional[str]
    sent_at: datetime

    class Config:
        from_attributes = True
