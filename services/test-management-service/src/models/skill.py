from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from src.db.session import Base

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Relationship to TestSkill association object
    test_skills = relationship("TestSkill", back_populates="skill", cascade="all, delete-orphan")

    # Convenience read-only relationship to Tests
    tests = relationship("Test", secondary="test_skills", viewonly=True)

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}')>"
