from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from src.db.init_db import Base
from src.config.settings import settings

# Import all models to register them with Base metadata
from src.models.user import User

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
        # Import all models here so they are registered with Base
        from src.models.user import User

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ DB connected successfully and tables are ready.")
    except OperationalError as e:
        print("❌ DB connection failed!")
        print(str(e))
