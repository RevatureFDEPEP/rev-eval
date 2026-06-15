"""Aggregate report query tests (W4-F3).

The require_trainer gate is dependency-overridden here (its own matrix lives
in test_auth_dependency.py) so these tests assert the SQL: GROUP BY values,
HAVING via min_attempts, filters, RANK ordering and histogram buckets, all
against the seeded fixture.

Seed recap (conftest): SUBMITTED sessions only —
  test 1: S1 (user 42, score 50.0, 1800s), S5 (user 7, score 80.0, 900s)
  test 2: S2 (user 42, score 100.0, 1200s)
S3 (ACTIVE) and S4 (EXPIRED) must never count.
"""
import main
import pytest
from src.v1.dependencies.auth import require_trainer

AGGREGATE = "/v1/api/reports/aggregate"
TIMESERIES = "/v1/api/reports/timeseries"


@pytest.fixture
async def trainer_client(client):
    main.app.dependency_overrides[require_trainer] = lambda: {
        "sub": "1",
        "role": "TRAINER",
    }
    yield client
    main.app.dependency_overrides.pop(require_trainer, None)


def _by_test(body):
    return {row["test_id"]: row for row in body["items"]}


async def test_aggregate_groups_by_test_with_expected_values(trainer_client):
    resp = await trainer_client.get(AGGREGATE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pass_threshold"] == 70.0
    rows = _by_test(body)
    assert set(rows) == {1, 2}

    t1 = rows[1]
    assert t1["test_name"] == "Java Fundamentals Quiz"
    assert t1["total_attempts"] == 2  # S1 + S5; ACTIVE S3 excluded
    assert t1["distinct_candidates"] == 2  # users 42 and 7
    assert t1["avg_score"] == 65.0  # (50 + 80) / 2
    assert t1["pass_rate"] == 50.0  # only S5's 80 >= 70
    assert t1["median_duration_seconds"] == 1350.0  # avg(900, 1800), even count

    t2 = rows[2]
    assert t2["total_attempts"] == 1  # S2; EXPIRED S4 excluded
    assert t2["distinct_candidates"] == 1
    assert t2["avg_score"] == 100.0
    assert t2["pass_rate"] == 100.0
    assert t2["median_duration_seconds"] == 1200.0  # single row, odd count


async def test_aggregate_min_attempts_acts_as_having(trainer_client):
    resp = await trainer_client.get(AGGREGATE, params={"min_attempts": 2})
    assert resp.status_code == 200
    rows = _by_test(resp.json())
    assert set(rows) == {1}  # test 2 has one attempt -> dropped by HAVING


async def test_aggregate_test_filter(trainer_client):
    resp = await trainer_client.get(AGGREGATE, params={"test_id": 2})
    assert resp.status_code == 200
    rows = _by_test(resp.json())
    assert set(rows) == {2}


async def test_aggregate_date_filter_bounds_attempt_start(trainer_client):
    # S1 started 06-01, S5 06-02, S2 06-03
    resp = await trainer_client.get(AGGREGATE, params={"from": "2026-06-03"})
    assert resp.status_code == 200
    rows = _by_test(resp.json())
    assert set(rows) == {2}

    resp = await trainer_client.get(AGGREGATE, params={"to": "2026-06-02"})
    rows = _by_test(resp.json())
    assert set(rows) == {1}


async def test_aggregate_rejects_bad_min_attempts(trainer_client):
    resp = await trainer_client.get(AGGREGATE, params={"min_attempts": 0})
    assert resp.status_code == 422


async def test_question_difficulty_rank_and_histogram(trainer_client):
    resp = await trainer_client.get("/v1/api/reports/test/1/questions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["test_id"] == 1
    assert body["test_name"] == "Java Fundamentals Quiz"

    items = body["items"]
    # Hardest first: qb (0%), qc (0%) tie at rank 1; qa (50%) rank 3.
    assert [i["question_id"] for i in items] == ["qb", "qc", "qa"]
    assert [i["difficulty_rank"] for i in items] == [1, 1, 3]

    by_q = {i["question_id"]: i for i in items}
    # qa: S1 perfect 1.0 + S5 partial 0.8; ACTIVE S3's answer must not count.
    assert by_q["qa"]["attempts"] == 2
    assert by_q["qa"]["correct_rate"] == 50.0
    assert by_q["qa"]["histogram"] == {
        "bucket_0_25": 0,
        "bucket_25_50": 0,
        "bucket_50_75": 0,
        "bucket_75_100": 2,
    }
    assert by_q["qb"]["correct_rate"] == 0.0
    assert by_q["qb"]["histogram"]["bucket_50_75"] == 1  # score 0.5
    assert by_q["qc"]["histogram"]["bucket_0_25"] == 1  # score 0.0


async def test_question_difficulty_all_correct_test(trainer_client):
    resp = await trainer_client.get("/v1/api/reports/test/2/questions")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {i["question_id"] for i in items} == {"qd", "qe"}
    assert all(i["correct_rate"] == 100.0 for i in items)
    assert all(i["difficulty_rank"] == 1 for i in items)  # full tie


async def test_question_difficulty_unknown_test_is_404(trainer_client):
    resp = await trainer_client.get("/v1/api/reports/test/999/questions")
    assert resp.status_code == 404


def _cells(body):
    """(date, test_id) -> attempts."""
    return {(r["date"], r["test_id"]): r["attempts"] for r in body["items"]}


async def test_timeseries_groups_by_day_and_test(trainer_client):
    # SUBMITTED submitted_at: S1 06-01 t1, S5 06-02 t1, S2 06-03 t2.
    resp = await trainer_client.get(TIMESERIES)
    assert resp.status_code == 200
    body = resp.json()
    cells = _cells(body)
    assert cells == {
        ("2026-06-01", 1): 1,
        ("2026-06-02", 1): 1,
        ("2026-06-03", 2): 1,
    }
    # Ordered (date, test_id) for stable client rendering.
    dates = [r["date"] for r in body["items"]]
    assert dates == sorted(dates)
    # test_name is carried for the per-quiz line labels.
    assert body["items"][0]["test_name"] == "Java Fundamentals Quiz"


async def test_timeseries_test_filter_narrows_series(trainer_client):
    resp = await trainer_client.get(TIMESERIES, params={"test_id": 1})
    assert resp.status_code == 200
    cells = _cells(resp.json())
    assert cells == {("2026-06-01", 1): 1, ("2026-06-02", 1): 1}


async def test_timeseries_date_range_bounds_attempt_start(trainer_client):
    resp = await trainer_client.get(TIMESERIES, params={"from": "2026-06-03"})
    assert resp.status_code == 200
    cells = _cells(resp.json())
    assert cells == {("2026-06-03", 2): 1}

    resp = await trainer_client.get(TIMESERIES, params={"to": "2026-06-01"})
    cells = _cells(resp.json())
    assert cells == {("2026-06-01", 1): 1}


async def test_timeseries_excludes_active_and_expired(trainer_client):
    # 3 SUBMITTED sessions seeded; ACTIVE S3 + EXPIRED S4 must not appear.
    resp = await trainer_client.get(TIMESERIES)
    assert sum(r["attempts"] for r in resp.json()["items"]) == 3
