# src/schemas/test_submission_schema.py
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, Any
from enum import Enum

class SubmissionStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EVALUATED = "EVALUATED"  # AI evaluation complete, awaiting trainer review
    GRADED = "GRADED"  # Trainer has reviewed and scored
    ABANDONED = "ABANDONED"

class TestSubmissionBase(BaseModel):
    test_id: int
    user_id: int
    assigned_by_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: Optional[SubmissionStatus] = SubmissionStatus.ASSIGNED

class TestSubmissionCreate(TestSubmissionBase):
    """Create schema with timezone stripping for POC"""
    
    @field_validator('due_date', mode='before')
    @classmethod
    def strip_timezone_from_due_date(cls, v: Any) -> Any:
        """Remove timezone for POC - TODO: fix with timezone-aware DB"""
        if v is not None and isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v
    
    class Config:
        from_attributes = True

class TestSubmissionUpdate(BaseModel):
    due_date: Optional[datetime] = None
    status: Optional[SubmissionStatus] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    ai_score: Optional[int] = None
    trainer_score: Optional[int] = None
    final_score: Optional[int] = None
    feedback: Optional[str] = None
    
    @field_validator('due_date', mode='before')
    @classmethod
    def strip_timezone_from_due_date(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v
    
    @field_validator('started_at', mode='before')
    @classmethod
    def strip_timezone_from_started_at(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v
    
    @field_validator('submitted_at', mode='before')
    @classmethod
    def strip_timezone_from_submitted_at(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v
    
    class Config:
        from_attributes = True

class TestInfo(BaseModel):
    """Minimal test information for submission display"""
    id: int
    name: str
    test_type: str
    role: Optional[str] = None
    curriculum: Optional[str] = None

    class Config:
        from_attributes = True

class TestSubmissionOut(TestSubmissionBase):
    id: int
    assigned_at: datetime
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus
    ai_score: Optional[int] = None
    trainer_score: Optional[int] = None
    final_score: Optional[int] = None
    feedback: Optional[str] = None
    reviewed_at: Optional[datetime] = None  # When trainer reviewed
    reviewed_by_id: Optional[int] = None  # Trainer user ID who reviewed
    created_at: datetime
    updated_at: datetime
    test: Optional[TestInfo] = None  # Eager-loaded test relationship
    participant_name: Optional[str] = None  # Fetched from User Service
    participant_email: Optional[str] = None  # Fetched from User Service

    class Config:
        from_attributes = True

class BulkAssignRequest(BaseModel):
    test_id: int
    participant_emails: list[str]
    due_date: Optional[datetime] = None
    # Note: assigned_by_id is extracted from JWT by get_current_user_from_headers dependency

    @field_validator('due_date', mode='before')
    @classmethod
    def strip_timezone_from_due_date(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

    class Config:
        from_attributes = True

class BulkAssignResult(BaseModel):
    success_count: int
    failure_count: int
    created_submissions: list[TestSubmissionOut]
    errors: list[dict]

    class Config:
        from_attributes = True


class TrainerReviewRequest(BaseModel):
    """Trainer's review submission"""
    trainer_score: int  # Required: trainer's final score (0-100)
    feedback: Optional[str] = None  # Optional feedback from trainer (deprecated, use trainer_evaluation)
    trainer_evaluation: Optional[dict] = None  # Comprehensive trainer evaluation structure

    class Config:
        from_attributes = True


class TrainerReviewResponse(BaseModel):
    """Response after trainer review"""
    submission_id: int
    trainer_score: int
    final_score: int
    ai_score: Optional[int] = None
    feedback: Optional[str] = None
    reviewed_at: datetime
    reviewed_by_id: int
    status: SubmissionStatus

    class Config:
        from_attributes = True