# src/scoring/__init__.py
"""Pure, deterministic question-scoring algorithms (W3-F2).

Each module exposes a single side-effect-free
``score_question(question_type, correct_answers, submitted_answers) -> ScoreResult``
function with no database access, so the algorithms can be unit-tested in
isolation and reused independently of the answer-submission endpoint.
"""
from src.scoring.result import ScoreResult

__all__ = ["ScoreResult"]
