from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.models.models import SCORED_STATUSES, Skill, Test, TestSubmission
from src.schemas.report_schemas import (
    DashboardReport,
    ParticipantReport,
    SkillSummary,
    SubmissionDetail,
    TestReport,
)

PASSING_SCORE = settings.PASSING_SCORE


def _score_stats(scores: list[int]) -> tuple[float | None, float | None]:
    if not scores:
        return None, None
    avg = round(sum(scores) / len(scores), 2)
    pass_rate = round(sum(1 for s in scores if s >= PASSING_SCORE) / len(scores) * 100, 2)
    return avg, pass_rate


def _submission_to_detail(sub: TestSubmission, test_name: str, skill_names: list[str]) -> SubmissionDetail:
    scored = sub.status in SCORED_STATUSES
    passed = (sub.final_score is not None and sub.final_score >= PASSING_SCORE) if scored else None
    return SubmissionDetail(
        submission_id=sub.id,
        test_id=sub.test_id,
        test_name=test_name,
        status=sub.status.value if sub.status else "UNKNOWN",
        final_score=sub.final_score,
        passed=passed,
        submitted_at=sub.submitted_at.isoformat() if sub.submitted_at else None,
        skills=skill_names,
    )


async def get_dashboard(db: AsyncSession) -> DashboardReport:
    tests_result = await db.execute(
        select(Test)
        .options(selectinload(Test.submissions), selectinload(Test.test_skills).selectinload("skill"))
    )
    tests = tests_result.scalars().all()

    all_subs = [sub for t in tests for sub in t.submissions]
    completed = [s for s in all_subs if s.status in SCORED_STATUSES]
    scores = [s.final_score for s in completed if s.final_score is not None]
    avg, pass_rate = _score_stats(scores)

    test_summaries = []
    for test in tests:
        t_completed = [s for s in test.submissions if s.status in SCORED_STATUSES]
        t_scores = [s.final_score for s in t_completed if s.final_score is not None]
        t_avg, t_pass = _score_stats(t_scores)
        test_summaries.append({
            "test_id": test.id,
            "test_name": test.name,
            "test_type": test.test_type,
            "total_assigned": len(test.submissions),
            "total_completed": len(t_completed),
            "avg_score": t_avg,
            "pass_rate": t_pass,
        })

    skills_result = await db.execute(
        select(Skill).options(selectinload(Skill.test_skills).selectinload("test").selectinload(Test.submissions))
    )
    skills = skills_result.scalars().all()

    skill_summaries = []
    for skill in skills:
        skill_subs = [
            sub
            for ts in skill.test_skills
            for sub in ts.test.submissions
            if sub.status in SCORED_STATUSES
        ]
        s_scores = [s.final_score for s in skill_subs if s.final_score is not None]
        s_avg, s_pass = _score_stats(s_scores)
        skill_summaries.append(SkillSummary(
            skill_id=skill.id,
            skill_name=skill.name,
            total_submissions=len(skill_subs),
            avg_score=s_avg,
            pass_rate=s_pass,
        ))

    total = len(all_subs)
    return DashboardReport(
        total_submissions=total,
        total_completed=len(completed),
        completion_rate=round(len(completed) / total * 100, 2) if total else 0.0,
        avg_score=avg,
        pass_rate=pass_rate,
        tests=test_summaries,
        skills=skill_summaries,
    )


async def get_test_report(db: AsyncSession, test_id: int) -> TestReport:
    result = await db.execute(
        select(Test)
        .where(Test.id == test_id)
        .options(selectinload(Test.submissions), selectinload(Test.test_skills).selectinload("skill"))
    )
    test = result.scalar_one_or_none()
    if not test:
        return None

    skill_names = [ts.skill.name for ts in test.test_skills if ts.skill]
    completed = [s for s in test.submissions if s.status in SCORED_STATUSES]
    scores = [s.final_score for s in completed if s.final_score is not None]
    avg, pass_rate = _score_stats(scores)
    total = len(test.submissions)

    submission_details = [
        _submission_to_detail(s, test.name, skill_names) for s in test.submissions
    ]

    return TestReport(
        test_id=test.id,
        test_name=test.name,
        test_type=test.test_type,
        role=test.role,
        curriculum=test.curriculum,
        total_assigned=total,
        total_completed=len(completed),
        completion_rate=round(len(completed) / total * 100, 2) if total else 0.0,
        avg_score=avg,
        pass_rate=pass_rate,
        skills=skill_names,
        submissions=submission_details,
    )


async def get_participant_report(db: AsyncSession, user_id: int) -> ParticipantReport:
    result = await db.execute(
        select(TestSubmission)
        .where(TestSubmission.user_id == user_id)
        .options(selectinload(TestSubmission.test).selectinload(Test.test_skills).selectinload("skill"))
    )
    subs = result.scalars().all()

    completed = [s for s in subs if s.status in SCORED_STATUSES]
    scores = [s.final_score for s in completed if s.final_score is not None]
    avg, pass_rate = _score_stats(scores)

    skills_covered = list({
        ts.skill.name
        for s in subs
        for ts in s.test.test_skills
        if ts.skill
    })

    details = [
        _submission_to_detail(
            s,
            s.test.name,
            [ts.skill.name for ts in s.test.test_skills if ts.skill],
        )
        for s in subs
    ]

    return ParticipantReport(
        user_id=user_id,
        total_assigned=len(subs),
        total_completed=len(completed),
        avg_score=avg,
        pass_rate=pass_rate,
        skills_covered=skills_covered,
        submissions=details,
    )


async def get_skills_report(db: AsyncSession) -> list[SkillSummary]:
    result = await db.execute(
        select(Skill).options(
            selectinload(Skill.test_skills).selectinload("test").selectinload(Test.submissions)
        )
    )
    skills = result.scalars().all()

    summaries = []
    for skill in skills:
        skill_subs = [
            sub
            for ts in skill.test_skills
            for sub in ts.test.submissions
            if sub.status in SCORED_STATUSES
        ]
        scores = [s.final_score for s in skill_subs if s.final_score is not None]
        avg, pass_rate = _score_stats(scores)
        summaries.append(SkillSummary(
            skill_id=skill.id,
            skill_name=skill.name,
            total_submissions=len(skill_subs),
            avg_score=avg,
            pass_rate=pass_rate,
        ))

    return summaries
