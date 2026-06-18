from typing import Dict, List, Optional

from pydantic import BaseModel


class ScoreStats(BaseModel):
    count: int
    min: Optional[float] = None
    max: Optional[float] = None
    average: Optional[float] = None
    median: Optional[float] = None


class OverviewReport(BaseModel):
    total_tests: int
    total_submissions: int
    by_status: Dict[str, int]
    completion_rate: float
    score: ScoreStats


class TestReport(BaseModel):
    test_id: int
    name: Optional[str] = None
    submission_count: int
    by_status: Dict[str, int]
    completion_rate: float
    score: ScoreStats


class ParticipantTestEntry(BaseModel):
    test_id: int
    name: Optional[str] = None
    status: Optional[str] = None
    final_score: Optional[float] = None


class ParticipantReport(BaseModel):
    user_id: int
    assigned: int
    completed: int
    average_final_score: Optional[float] = None
    tests: List[ParticipantTestEntry]


# --- Candidate-facing reporting (Day 16) -------------------------------------


class CandidateReport(BaseModel):
    """Summary of one candidate's attempts.

    Readable by the candidate themselves (self-read) or any trainer/admin.
    ``score`` aggregates only attempts that have an effective score, so unscored
    assignments never drag the average toward zero.
    """
    user_id: int
    assigned: int
    completed: int
    in_progress: int
    by_status: Dict[str, int]
    average_final_score: Optional[float] = None
    best_score: Optional[float] = None
    score: ScoreStats


class AttemptEntry(BaseModel):
    submission_id: Optional[int] = None
    test_id: Optional[int] = None
    test_name: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    assigned_at: Optional[str] = None
    submitted_at: Optional[str] = None


class PaginatedAttempts(BaseModel):
    """Page of a candidate's attempts with the applied query echoed back."""
    user_id: int
    total: int
    page: int
    page_size: int
    sort: str
    order: str
    status: Optional[str] = None
    items: List[AttemptEntry]
