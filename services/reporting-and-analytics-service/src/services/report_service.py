from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.models.models import SCORED_STATUSES, Skill, Test, TestSkill, TestSubmission
from src.schemas.report_schemas import (
    DashboardReport,
    ParticipantReport,
    SkillSummary,
    SubmissionDetail,
    TestReport,
)

PASSING_SCORE = settings.PASSING_SCORE
_SCORED_VALUES = [s.value for s in SCORED_STATUSES]


# ---------------------------------------------------------------------------
# SQL expression helpers
# ---------------------------------------------------------------------------

def _is_scored():
    return TestSubmission.status.in_(_SCORED_VALUES)


def _has_score():
    return and_(_is_scored(), TestSubmission.final_score.isnot(None))


def _is_passed():
    return and_(_has_score(), TestSubmission.final_score >= PASSING_SCORE)


def _agg_cols():
    """Standard aggregate columns reused across queries."""
    return (
        func.count(TestSubmission.id).label("total"),
        func.count(case((_is_scored(), 1))).label("completed"),
        func.avg(case((_has_score(), TestSubmission.final_score))).label("avg_score"),
        func.count(case((_has_score(), 1))).label("scored_count"),
        func.count(case((_is_passed(), 1))).label("passed_count"),
    )


# ---------------------------------------------------------------------------
# Python-side helpers (shaping only, no iteration over large sets)
# ---------------------------------------------------------------------------

def _to_float(value) -> float | None:
    return round(float(value), 2) if value is not None else None


def _pass_rate(passed: int, scored: int) -> float | None:
    if not scored:
        return None
    return round(passed / scored * 100, 2)


def _submission_to_detail(sub: TestSubmission, test_name: str, skill_names: list[str]) -> SubmissionDetail:
    in_scored = sub.status in SCORED_STATUSES
    passed = (sub.final_score is not None and sub.final_score >= PASSING_SCORE) if in_scored else None
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


# ---------------------------------------------------------------------------
# Report functions
# ---------------------------------------------------------------------------

async def get_dashboard(db: AsyncSession) -> DashboardReport:
    # Overall totals — single row
    overall = (await db.execute(select(*_agg_cols()))).one()

    # Per-test — one row per test via GROUP BY
    test_rows = (await db.execute(
        select(Test.id, Test.name, Test.test_type, *_agg_cols())
        .join(TestSubmission, TestSubmission.test_id == Test.id, isouter=True)
        .group_by(Test.id, Test.name, Test.test_type)
        .order_by(Test.id)
    )).all()

    test_summaries = [
        {
            "test_id": row.id,
            "test_name": row.name,
            "test_type": row.test_type,
            "total_assigned": row.total,
            "total_completed": row.completed,
            "avg_score": _to_float(row.avg_score),
            "pass_rate": _pass_rate(row.passed_count, row.scored_count),
        }
        for row in test_rows
    ]

    # Per-skill — one row per skill via GROUP BY (only scored submissions)
    skill_rows = (await db.execute(
        select(
            Skill.id,
            Skill.name,
            func.count(TestSubmission.id).label("total"),
            func.avg(case((_has_score(), TestSubmission.final_score))).label("avg_score"),
            func.count(case((_has_score(), 1))).label("scored_count"),
            func.count(case((_is_passed(), 1))).label("passed_count"),
        )
        .join(TestSkill, TestSkill.skill_id == Skill.id)
        .join(TestSubmission, TestSubmission.test_id == TestSkill.test_id)
        .where(_is_scored())
        .group_by(Skill.id, Skill.name)
        .order_by(Skill.id)
    )).all()

    skill_summaries = [
        SkillSummary(
            skill_id=row.id,
            skill_name=row.name,
            total_submissions=row.total,
            avg_score=_to_float(row.avg_score),
            pass_rate=_pass_rate(row.passed_count, row.scored_count),
        )
        for row in skill_rows
    ]

    total = overall.total or 0
    completed = overall.completed or 0
    return DashboardReport(
        total_submissions=total,
        total_completed=completed,
        completion_rate=round(completed / total * 100, 2) if total else 0.0,
        avg_score=_to_float(overall.avg_score),
        pass_rate=_pass_rate(overall.passed_count, overall.scored_count),
        tests=test_summaries,
        skills=skill_summaries,
    )


async def get_test_report(db: AsyncSession, test_id: int) -> TestReport | None:
    # Test metadata + skills
    test_result = await db.execute(
        select(Test)
        .where(Test.id == test_id)
        .options(selectinload(Test.test_skills).selectinload(TestSkill.skill))
    )
    test = test_result.scalar_one_or_none()
    if not test:
        return None

    skill_names = [ts.skill.name for ts in test.test_skills if ts.skill]

    # Aggregate stats — one query
    agg = (await db.execute(
        select(*_agg_cols()).where(TestSubmission.test_id == test_id)
    )).one()

    # Submission details — rows still needed for the detail list
    subs_result = await db.execute(
        select(TestSubmission)
        .where(TestSubmission.test_id == test_id)
        .order_by(TestSubmission.id)
    )
    subs = subs_result.scalars().all()

    total = agg.total or 0
    completed = agg.completed or 0
    return TestReport(
        test_id=test.id,
        test_name=test.name,
        test_type=test.test_type,
        role=test.role,
        curriculum=test.curriculum,
        total_assigned=total,
        total_completed=completed,
        completion_rate=round(completed / total * 100, 2) if total else 0.0,
        avg_score=_to_float(agg.avg_score),
        pass_rate=_pass_rate(agg.passed_count, agg.scored_count),
        skills=skill_names,
        submissions=[_submission_to_detail(s, test.name, skill_names) for s in subs],
    )


async def get_participant_report(db: AsyncSession, user_id: int) -> ParticipantReport:
    # Aggregate stats — one query
    agg = (await db.execute(
        select(*_agg_cols()).where(TestSubmission.user_id == user_id)
    )).one()

    # Skills covered — distinct via join, no Python set comprehension over rows
    skills_result = await db.execute(
        select(distinct(Skill.name))
        .join(TestSkill, TestSkill.skill_id == Skill.id)
        .join(TestSubmission, TestSubmission.test_id == TestSkill.test_id)
        .where(TestSubmission.user_id == user_id)
        .order_by(Skill.name)
    )
    skills_covered = [row[0] for row in skills_result.all()]

    # Submission details with test + skill names (row fetch still needed for detail list)
    subs_result = await db.execute(
        select(TestSubmission)
        .where(TestSubmission.user_id == user_id)
        .options(selectinload(TestSubmission.test).selectinload(Test.test_skills).selectinload(TestSkill.skill))
        .order_by(TestSubmission.id)
    )
    subs = subs_result.scalars().all()

    total = agg.total or 0
    completed = agg.completed or 0
    return ParticipantReport(
        user_id=user_id,
        total_assigned=total,
        total_completed=completed,
        avg_score=_to_float(agg.avg_score),
        pass_rate=_pass_rate(agg.passed_count, agg.scored_count),
        skills_covered=skills_covered,
        submissions=[
            _submission_to_detail(
                s,
                s.test.name,
                [ts.skill.name for ts in s.test.test_skills if ts.skill],
            )
            for s in subs
        ],
    )


async def get_skills_report(db: AsyncSession) -> list[SkillSummary]:
    rows = (await db.execute(
        select(
            Skill.id,
            Skill.name,
            func.count(TestSubmission.id).label("total"),
            func.avg(case((_has_score(), TestSubmission.final_score))).label("avg_score"),
            func.count(case((_has_score(), 1))).label("scored_count"),
            func.count(case((_is_passed(), 1))).label("passed_count"),
        )
        .join(TestSkill, TestSkill.skill_id == Skill.id)
        .join(TestSubmission, TestSubmission.test_id == TestSkill.test_id)
        .where(_is_scored())
        .group_by(Skill.id, Skill.name)
        .order_by(Skill.id)
    )).all()

    return [
        SkillSummary(
            skill_id=row.id,
            skill_name=row.name,
            total_submissions=row.total,
            avg_score=_to_float(row.avg_score),
            pass_rate=_pass_rate(row.passed_count, row.scored_count),
        )
        for row in rows
    ]
