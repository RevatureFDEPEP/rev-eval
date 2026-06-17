import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(64), nullable=False, unique=True)
    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(SessionStatus, name="sessionstatus"), nullable=False, default=SessionStatus.ACTIVE)
    current_index = Column(Integer, nullable=False, default=0)
