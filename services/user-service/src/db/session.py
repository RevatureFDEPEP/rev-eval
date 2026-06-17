from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from src.db.init_db import Base, SessionLocal, engine


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

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ DB connected successfully and tables are ready.")
    except OperationalError as e:
        print("❌ DB connection failed!")
        print(str(e))
