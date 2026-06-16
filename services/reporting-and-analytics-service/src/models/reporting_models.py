from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from src.db.session import Base


class Test(Base):
    __tablename__ = "tests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    active = Column(Boolean, server_default="true")
    created_at = Column(DateTime, nullable=True)


class TestSubmission(Base):
    __tablename__ = "test_submissions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=True)
    final_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    submission_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False)
    percentage_score = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
