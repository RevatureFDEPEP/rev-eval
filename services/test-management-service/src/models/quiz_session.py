import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(36), unique=True, nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False)
    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
