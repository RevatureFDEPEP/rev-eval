# src/models/test.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Interval, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.session import Base
import enum

class TestType(str, enum.Enum):
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
