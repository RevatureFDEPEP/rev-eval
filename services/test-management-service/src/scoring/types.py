from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ScoreResult:
    """Result of scoring a single question.

    earned/possible are in the same unit (1.0 == full marks for the question).
    is_correct is True only on an exact match, regardless of partial credit.
    details carries auditable counts for debugging/reporting.
    """

    earned: float
    possible: float
    is_correct: bool
    details: Dict[str, Any] = field(default_factory=dict)
