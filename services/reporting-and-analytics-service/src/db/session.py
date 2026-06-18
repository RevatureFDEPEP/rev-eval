from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import settings

EvalAiBase = declarative_base()

eval_ai_engine = create_engine(settings.EVAL_AI_SQLALCHEMY_DATABASE_URL)
EvalAiSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=eval_ai_engine
)


def get_eval_ai_db():
    db = EvalAiSessionLocal()
    try:
        yield db
    finally:
        db.close()
