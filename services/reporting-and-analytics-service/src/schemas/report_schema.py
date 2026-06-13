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
