"""Pure, side-effect-free analytics helpers.

No I/O, no framework types — trivially unit-testable. Routes fetch raw
submission/test dicts from test-management-service and feed them here.
"""
from typing import Any, Dict, List, Optional

# Submission statuses that count as a finished attempt for completion rate.
COMPLETED_STATUSES = {"COMPLETED", "EVALUATED", "GRADED"}


def effective_score(submission: Dict[str, Any]) -> Optional[float]:
    """The score that best represents a submission's outcome.

    Prefer the trainer-confirmed final score, then trainer score, then the
    AI score. Returns None when nothing has been scored yet so unscored
    attempts are excluded from averages rather than counted as zero.
    """
    for key in ("final_score", "trainer_score", "ai_score"):
        value = submission.get(key)
        if value is not None:
            return float(value)
    return None


def score_stats(values: List[Optional[float]]) -> Dict[str, Any]:
    """Min/max/mean/median over the non-null numeric values."""
    nums = sorted(float(v) for v in values if v is not None)
    n = len(nums)
    if n == 0:
        return {"count": 0, "min": None, "max": None, "average": None, "median": None}

    mid = n // 2
    median = nums[mid] if n % 2 == 1 else (nums[mid - 1] + nums[mid]) / 2.0

    return {
        "count": n,
        "min": nums[0],
        "max": nums[-1],
        "average": round(sum(nums) / n, 2),
        "median": round(median, 2),
    }


def status_breakdown(submissions: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count submissions per status."""
    counts: Dict[str, int] = {}
    for sub in submissions:
        status = str(sub.get("status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def completion_rate(submissions: List[Dict[str, Any]]) -> float:
    """Fraction of submissions in a completed/graded state (0.0–1.0)."""
    total = len(submissions)
    if total == 0:
        return 0.0
    done = sum(1 for s in submissions if str(s.get("status")) in COMPLETED_STATUSES)
    return round(done / total, 4)
