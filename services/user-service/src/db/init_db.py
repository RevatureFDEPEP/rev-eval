# src/db/init.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config.settings import settings

# SQLAlchemy engine
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=True,           # optional: logs SQL queries
    future=True          # use SQLAlchemy 2.x style
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI (optional)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()