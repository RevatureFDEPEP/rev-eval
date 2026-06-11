import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SubmissionStatus(enum.StrEnum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EVALUATED = "EVALUATED"
    GRADED = "GRADED"
    ABANDONED = "ABANDONED"


SCORED_STATUSES = {SubmissionStatus.COMPLETED, SubmissionStatus.EVALUATED, SubmissionStatus.GRADED}


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    test_type = Column(String(50))
    role = Column(String(100))
    curriculum = Column(String(255))
    created_by_id = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime)

    submissions = relationship("TestSubmission", back_populates="test")
    test_skills = relationship("TestSkill", back_populates="test")


class TestSubmission(Base):
    __tablename__ = "test_submissions"

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"))
    user_id = Column(Integer)
    assigned_by_id = Column(Integer)
    status = Column(Enum(SubmissionStatus))
    assigned_at = Column(DateTime)
    due_date = Column(DateTime)
    submitted_at = Column(DateTime)
    final_score = Column(Integer)
    ai_score = Column(Integer)
    trainer_score = Column(Integer)
    feedback = Column(Text)

    test = relationship("Test", back_populates="submissions")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(Text)

    test_skills = relationship("TestSkill", back_populates="skill")


class TestSkill(Base):
    __tablename__ = "test_skills"

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"))
    skill_id = Column(Integer, ForeignKey("skills.id"))

    __table_args__ = (UniqueConstraint("test_id", "skill_id"),)

    test = relationship("Test", back_populates="test_skills")
    skill = relationship("Skill", back_populates="test_skills")
