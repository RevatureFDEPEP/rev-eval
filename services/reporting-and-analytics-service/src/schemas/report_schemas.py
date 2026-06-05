from pydantic import BaseModel


class SubmissionDetail(BaseModel):
    submission_id: int
    test_id: int
    test_name: str
    status: str
    final_score: int | None
    passed: bool | None
    submitted_at: str | None
    skills: list[str]

    class Config:
        from_attributes = True


class TestReport(BaseModel):
    test_id: int
    test_name: str
    test_type: str | None
    role: str | None
    curriculum: str | None
    total_assigned: int
    total_completed: int
    completion_rate: float
    avg_score: float | None
    pass_rate: float | None
    skills: list[str]
    submissions: list[SubmissionDetail]


class ParticipantReport(BaseModel):
    user_id: int
    total_assigned: int
    total_completed: int
    avg_score: float | None
    pass_rate: float | None
    skills_covered: list[str]
    submissions: list[SubmissionDetail]


class SkillSummary(BaseModel):
    skill_id: int
    skill_name: str
    total_submissions: int
    avg_score: float | None
    pass_rate: float | None


class DashboardReport(BaseModel):
    total_submissions: int
    total_completed: int
    completion_rate: float
    avg_score: float | None
    pass_rate: float | None
    tests: list[dict]
    skills: list[SkillSummary]
