from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.session import Base
import enum


class UserRole(str, enum.Enum):
    """User roles in the system"""
    TRAINER = "TRAINER"
    PARTICIPANT = "PARTICIPANT"

class User(Base):
    """
    Unified user model for both trainers and participants.
    Synced with WorkOS authentication.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    workos_user_id = Column(String(255), nullable=True, unique=True, index=True)  # WorkOS 'sub' claim
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    organization_id = Column(String(255), nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
