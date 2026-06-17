"""Cross-schema integration tests: reporting's queries vs the REAL test-management
Postgres schema.

These are the load-bearing guard the hermetic suite cannot be: the hermetic
tests build their schema from reporting's own ``tms_readonly`` mirror, so they
stay green even if that mirror drifts from what test-management actually
migrates. Here the schema is test-management's real one (enum type, column
names, NULL semantics), so drift fails the run.
"""

from src.models.tms_readonly import QuizSessionStatus
from src.schemas.reporting_schema import SORTABLE_FIELDS, AttemptsQuery
from src.services.reporting_service import ReportingService


class TestSummaryRealSchema:
    async def test_summary_numbers(self, real_session, seeded_real):
        s = await ReportingService.get_user_summary(
            real_session, seeded_real["user_id"]
        )
        assert s.total_attempts == 2
        assert s.average_score == 0.5
        assert s.best_score == 0.5
        assert s.total_time_spent_seconds == 600
        assert s.most_recent_attempt is not None
        assert s.most_recent_attempt.session_id == "it_rs2"  # created 11:00
        assert s.most_recent_attempt.status == QuizSessionStatus.ACTIVE


class TestAttemptsRealSchema:
    async def test_default_sort_nulls_last(self, real_session, seeded_real):
        page = await ReportingService.get_user_attempts(
            real_session, seeded_real["user_id"], AttemptsQuery(size=10)
        )
        assert page.total == 2
        # submitted_at desc, NULLS LAST → submitted it_rs1 first, then null it_rs2
        assert [i.session_id for i in page.items] == ["it_rs1", "it_rs2"]

    async def test_enum_status_filter_binds_on_pg(self, real_session, seeded_real):
        # The key dialect risk: status is a native PG enum (quizsessionstatus).
        submitted = await ReportingService.get_user_attempts(
            real_session,
            seeded_real["user_id"],
            AttemptsQuery(size=10, status=QuizSessionStatus.SUBMITTED),
        )
        assert [i.session_id for i in submitted.items] == ["it_rs1"]
        assert submitted.items[0].score == 0.5

        active = await ReportingService.get_user_attempts(
            real_session,
            seeded_real["user_id"],
            AttemptsQuery(size=10, status=QuizSessionStatus.ACTIVE),
        )
        assert [i.session_id for i in active.items] == ["it_rs2"]

    async def test_test_id_filter_and_join(self, real_session, seeded_real):
        page = await ReportingService.get_user_attempts(
            real_session,
            seeded_real["user_id"],
            AttemptsQuery(size=10, test_id=seeded_real["test_id"]),
        )
        assert page.total == 2
        assert all(i.test_name == "IT Reporting Test" for i in page.items)

    async def test_every_sortable_field_resolves(self, real_session, seeded_real):
        # Each declared sort column must exist on the real table (catches a
        # renamed/dropped order column, which would throw only on real PG).
        for field in SORTABLE_FIELDS:
            for direction in ("asc", "desc"):
                page = await ReportingService.get_user_attempts(
                    real_session,
                    seeded_real["user_id"],
                    AttemptsQuery(size=10, sort=f"{field}:{direction}"),
                )
                assert page.total == 2
