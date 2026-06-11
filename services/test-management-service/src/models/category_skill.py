from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db.session import Base


class CategorySkill(Base):
    """
    Association model for many-to-many relationship between Category and Skill.
    Can be extended to store metadata like weight, importance, etc.
    """
    __tablename__ = "category_skills"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)

    __table_args__ = (UniqueConstraint("category_id", "skill_id", name="uq_category_skill"),)

    # Relationships
    category = relationship("Category", back_populates="category_skills")
    skill = relationship("Skill", back_populates="category_skills")
