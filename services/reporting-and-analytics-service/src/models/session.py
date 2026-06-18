import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON

from src.db.session import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(64), nullable=False)
    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    # create_type=False: the enum type already exists in Postgres, owned by test-management-service
    status = Column(Enum(SessionStatus, name="sessionstatus", create_type=False), nullable=False)
    current_index = Column(Integer, nullable=False)
    question_ids = Column(JSON, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
