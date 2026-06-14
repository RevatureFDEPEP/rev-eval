from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from src.db.session import Base

skill_categories = Table(
    "skill_categories",
    Base.metadata,
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    skills = relationship("Skill", secondary=skill_categories, back_populates="categories")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
