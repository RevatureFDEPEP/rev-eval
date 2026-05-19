from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.db.session import Base

class TestSkill(Base):
    """
    Association model for many-to-many relationship between Test and Skill.
    Can be extended to store metadata like weight, importance, etc.
    """
    __tablename__ = "test_skills"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)

    __table_args__ = (UniqueConstraint("test_id", "skill_id", name="uq_test_skill"),)

    # Relationships
    test = relationship("Test", back_populates="test_skills")
    skill = relationship("Skill", back_populates="test_skills")
