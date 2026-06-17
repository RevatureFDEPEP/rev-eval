from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    earned: float
    max_points: float
    is_correct: bool
