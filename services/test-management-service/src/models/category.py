from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from src.db.session import Base

test_categories = Table(
    "test_categories",
    Base.metadata,
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
    Column("test_id", Integer, ForeignKey("tests.id"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    tests = relationship("Test", secondary="test_categories", back_populates="categories")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
