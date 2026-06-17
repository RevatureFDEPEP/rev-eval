"""Service-layer tests: aggregate correctness against the hand-computed seed."""

from src.models.tms_readonly import QuizSessionStatus
from src.schemas.reporting_schema import AttemptsQuery
from src.services.reporting_service import ReportingService


class TestUserSummary:
    async def test_aggregates_match_seed(self, session):
        s = await ReportingService.get_user_summary(session, 100)
        assert s.total_attempts == 4  # all sessions count as attempts
        # average/best over SUBMITTED only: s1=2/3, s2=0.75 → mean 0.7083.
        # s4 (EXPIRED, score 0.0) and s3 (ACTIVE, no answers) are excluded.
        assert s.average_score == 0.7083
        assert s.best_score == 0.75
        assert s.total_time_spent_seconds == 900  # s1 600 + s2 300

    async def test_expired_and_active_excluded_from_score(self, session):
        # Regression guard: counting the EXPIRED 0.0 would drop the average to 0.4722.
        s = await ReportingService.get_user_summary(session, 100)
        assert s.average_score == 0.7083

    async def test_most_recent_is_latest_created(self, session):
        s = await ReportingService.get_user_summary(session, 100)
        assert s.most_recent_attempt is not None
        assert s.most_recent_attempt.session_id == "s2"
        assert s.most_recent_attempt.score == 0.75
        assert s.most_recent_attempt.time_spent_seconds == 300

    async def test_unknown_user_is_empty_not_error(self, session):
        s = await ReportingService.get_user_summary(session, 999)
        assert s.total_attempts == 0
        assert s.average_score is None
        assert s.best_score is None
        assert s.total_time_spent_seconds == 0
        assert s.most_recent_attempt is None

    async def test_user_isolation(self, session):
        # user 200's single submitted session must not leak into user 100
        s100 = await ReportingService.get_user_summary(session, 100)
        s200 = await ReportingService.get_user_summary(session, 200)
        assert s100.total_attempts == 4
        assert s200.total_attempts == 1
        assert s200.best_score == 1.0


class TestUserAttempts:
    async def test_default_sort_submitted_desc_nulls_last(self, session):
        page = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(page=1, size=10)
        )
        assert page.total == 4
        ids = [i.session_id for i in page.items]
        # submitted desc → s2, s1; then NULL submitted (s3, s4) by session_id asc
        assert ids == ["s2", "s1", "s3", "s4"]

    async def test_pagination_meta(self, session):
        page1 = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(page=1, size=2)
        )
        assert (page1.page, page1.size, page1.total) == (1, 2, 4)
        assert [i.session_id for i in page1.items] == ["s2", "s1"]
        page2 = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(page=2, size=2)
        )
        assert [i.session_id for i in page2.items] == ["s3", "s4"]

    async def test_filter_status(self, session):
        page = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(size=10, status=QuizSessionStatus.SUBMITTED)
        )
        assert page.total == 2
        assert {i.session_id for i in page.items} == {"s1", "s2"}

    async def test_filter_test_id(self, session):
        page = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(size=10, test_id=1)
        )
        assert page.total == 3
        assert {i.session_id for i in page.items} == {"s1", "s3", "s4"}

    async def test_score_and_counts_per_attempt(self, session):
        page = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(size=10, test_id=2)
        )
        (item,) = page.items
        assert item.session_id == "s2"
        assert item.score == 0.75
        assert item.correct_count == 1
        assert item.total_answered == 2
        assert item.time_spent_seconds == 300

    async def test_answerless_attempt_has_null_score(self, session):
        page = await ReportingService.get_user_attempts(
            session, 100, AttemptsQuery(size=10, status=QuizSessionStatus.ACTIVE)
        )
        (item,) = page.items
        assert item.session_id == "s3"
        assert item.score is None
        assert item.total_answered == 0
