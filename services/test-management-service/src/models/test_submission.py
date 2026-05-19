from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.session import Base
import enum

class SubmissionStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EVALUATED = "EVALUATED"  # AI evaluation complete, awaiting trainer review
    GRADED = "GRADED"  # Trainer has reviewed and scored
    ABANDONED = "ABANDONED"

class TestSubmission(Base):
    __tablename__ = "test_submissions"
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to local Test table
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)

    # User IDs from external User Service
    user_id = Column(Integer, nullable=False)          # participant
    assigned_by_id = Column(Integer, nullable=True)    # trainer/admin

    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.ASSIGNED)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    ai_score = Column(Integer, nullable=True)
    trainer_score = Column(Integer, nullable=True)
    final_score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)  # When trainer reviewed
    reviewed_by_id = Column(Integer, nullable=True)  # Trainer user ID who reviewed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Local relationships only
    test = relationship("Test", back_populates="submissions")