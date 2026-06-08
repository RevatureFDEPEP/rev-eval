import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config.settings import settings

Base = declarative_base()

logger = logging.getLogger(__name__)

# Use settings for database URL
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ===== Dependency for FastAPI =====
def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== Initialize DB =====
def init_db():
    """
    Import all models, create tables, and test connection.
    Call this on app startup.
    """
    try:
        # Deferred import so the model registers with Base.metadata before
        # create_all, without a module-level session <-> user import cycle.
        from src.models import user  # noqa: F401

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("DB connected successfully and tables are ready.")
    except OperationalError:
        logger.error("DB connection failed!", exc_info=True)
