from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from src.db.session import Base


class SessionQuestion(Base):
    __tablename__ = "session_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    question_id = Column(String(24), nullable=False)

    __table_args__ = (UniqueConstraint("session_id", "position", name="uq_session_position"),)
