from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from src.db.session import Base


class CategorySkill(Base):
    """
    Association model for the many-to-many relationship between Category and
    Skill. Mirrors the TestSkill association-object pattern so it can later be
    extended with metadata (e.g. ordering, weight) without a schema rewrite.
    """

    __tablename__ = "category_skills"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("category_id", "skill_id", name="uq_category_skill"),
    )

    # Relationships
    category = relationship("Category", back_populates="category_skills")
    skill = relationship("Skill")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Relationship to CategorySkill association object
    category_skills = relationship(
        "CategorySkill", back_populates="category", cascade="all, delete-orphan"
    )

    # Convenience read-only relationship to Skills
    skills = relationship("Skill", secondary="category_skills", viewonly=True)

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
