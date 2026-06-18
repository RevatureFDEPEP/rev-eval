from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    score: float          # 0.0 – 1.0 normalised score
    is_correct: bool      # True only when full credit earned
    points_earned: float
    points_possible: float = 1.0
    details: str = ""
