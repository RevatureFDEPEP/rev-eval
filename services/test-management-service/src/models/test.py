# src/models/test.py
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, Interval, String
from sqlalchemy.orm import relationship
from src.db.session import Base


class TestType(enum.StrEnum):
    QUIZ = "QUIZ"
    INTERVIEW = "INTERVIEW"

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    test_type = Column(Enum(TestType), nullable=False, default=TestType.QUIZ)

    # Test metadata
    role = Column(String(100), nullable=True)
    curriculum = Column(String(255), nullable=True)
    duration = Column(Interval, nullable=True)
    number_of_questions = Column(Integer, nullable=True, default=20)

    # Creator info
    created_by_id = Column(Integer, nullable=True)

    # Status
    active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submissions = relationship("TestSubmission", back_populates="test", cascade="all, delete-orphan")
    test_skills = relationship("TestSkill", back_populates="test", cascade="all, delete-orphan")
