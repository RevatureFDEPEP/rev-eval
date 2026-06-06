from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from src.db.session import Base

# Plain association table: the category<->skill link carries no metadata,
# so no association model is needed (unlike TestSkill).
category_skills = Table(
    "category_skills",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
    Column("skill_id", Integer, ForeignKey("skills.id"), nullable=False),
    UniqueConstraint("category_id", "skill_id", name="uq_category_skill"),
)


class Category(Base):
    """A topic grouping for skills, e.g. "Python", "Docker", "Algorithms"."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # This side owns the link writes; Skill.categories is viewonly.
    skills = relationship("Skill", secondary=category_skills)

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
