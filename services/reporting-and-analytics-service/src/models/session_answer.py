from sqlalchemy import Column, Float, Integer, String

from src.db.session import EvalAiBase


class SessionAnswer(EvalAiBase):
    __tablename__ = "session_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    score = Column(Float, nullable=True)
