from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from datetime import datetime
from src.db.session import Base
import enum


class UserRole(str, enum.Enum):
    """User roles in the system"""
    TRAINER = "TRAINER"
    PARTICIPANT = "PARTICIPANT"


class User(Base):
    """Unified user model for trainers and participants."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    organization_id = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
