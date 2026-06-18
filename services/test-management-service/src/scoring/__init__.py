"""Pure scoring engine for the quiz-session backend (W3-F2).

Side-effect-free, deterministic, no I/O — no DB, no clock, no httpx. The route
layer fetches the correct-answer key from question-management-service and feeds
it into :func:`score_question`; this package never reaches the network or the
database, so it is unit-testable with plain ``pytest`` (no async runner, no live
datastore) and stays cheap to mutation-test.
"""

from src.scoring.engine import ScoreResult, score_question

__all__ = ["ScoreResult", "score_question"]
