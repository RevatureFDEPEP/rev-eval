from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from src.db.session import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to CategorySkill association object
    category_skills = relationship(
        "CategorySkill", back_populates="category", cascade="all, delete-orphan"
    )

    # Convenience read-only relationship to Skills
    skills = relationship("Skill", secondary="category_skills", viewonly=True)

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
