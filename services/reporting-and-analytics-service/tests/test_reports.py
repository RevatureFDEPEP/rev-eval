import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./reporting_test.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "reporting-and-analytics-service")
os.environ.setdefault("PASS_THRESHOLD", "70.0")

import asyncio
import time as _time
from datetime import datetime

import jwt as _jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from src.db.session import Base, engine, get_db
from src.models.reporting_models import QuizSession, Test, TestSubmission  # noqa: F401
from src.utils.dependencies import get_current_user, verify_jwt

TestingAsyncSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_create_tables())


async def _seed():
    async with TestingAsyncSession() as db:
        tests = [
            Test(id=1, name="Python Basics", active=True, created_at=datetime.utcnow()),
            Test(id=2, name="SQL Fundamentals", active=True, created_at=datetime.utcnow()),
            Test(id=3, name="Empty Test", active=True, created_at=datetime.utcnow()),
            Test(id=4, name="Questions Test", active=True, created_at=datetime.utcnow()),
        ]
        db.add_all(tests)
        await db.flush()

        now = datetime.utcnow()
        from datetime import timedelta
        sessions = [
            # test1 — 4 completed sessions
            QuizSession(id="s1", test_id=1, user_id=10, status="COMPLETED", percentage_score=85.0, started_at=now - timedelta(minutes=30), completed_at=now),
            QuizSession(id="s2", test_id=1, user_id=11, status="COMPLETED", percentage_score=62.5, started_at=now - timedelta(minutes=25), completed_at=now),
            QuizSession(id="s3", test_id=1, user_id=12, status="COMPLETED", percentage_score=91.0, started_at=now - timedelta(minutes=20), completed_at=now),
            QuizSession(id="s4", test_id=1, user_id=13, status="COMPLETED", percentage_score=45.0, started_at=now - timedelta(minutes=15), completed_at=now),
            # test2 — 1 completed session for user 10
            QuizSession(id="s5", test_id=2, user_id=10, status="COMPLETED", percentage_score=78.0, started_at=now - timedelta(minutes=10), completed_at=now),
            # test1 — abandoned (should NOT count in completed-only endpoints)
            QuizSession(id="s6", test_id=1, user_id=14, status="ABANDONED", percentage_score=None, started_at=None, completed_at=None),
            # test4 — 2 completed sessions with graded per-question data
            QuizSession(
                id="s8", test_id=4, user_id=20, status="COMPLETED", percentage_score=80.0,
                started_at=now - timedelta(minutes=5), completed_at=now,
                part_a={"questions": [
                    {"question_id": "qA1", "question_type": "mcq", "is_correct": True, "scored_value": 1.0},
                    {"question_id": "qA2", "question_type": "mcq", "is_correct": False, "scored_value": 0.0},
                ]},
                part_b={"questions": [
                    {"question_id": "qB1", "question_type": "multi", "is_correct": True, "scored_value": 1.0},
                ]},
            ),
            QuizSession(
                id="s9", test_id=4, user_id=21, status="COMPLETED", percentage_score=60.0,
                started_at=now - timedelta(minutes=3), completed_at=now,
                part_a={"questions": [
                    {"question_id": "qA1", "question_type": "mcq", "is_correct": False, "scored_value": 0.0},
                    {"question_id": "qA2", "question_type": "mcq", "is_correct": True, "scored_value": 1.0},
                ]},
                part_b=None,
            ),
        ]
        db.add_all(sessions)
        await db.commit()


asyncio.run(_seed())


async def override_get_db():
    async with TestingAsyncSession() as db:
        yield db


FAKE_TRAINER = {"sub": "1", "id": 1, "email": "trainer@test.com", "role": "TRAINER"}
FAKE_USER = {"sub": "10", "id": 10, "email": "user@test.com", "role": "PARTICIPANT"}


def override_verify_jwt_trainer():
    return FAKE_TRAINER


def override_verify_jwt_user():
    return FAKE_USER


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer

client = TestClient(app)


@pytest.fixture(autouse=True)
def _restore_trainer_override():
    """Re-set verify_jwt override before every test.

    test_auth_jwt.py's TestEndpointAuth removes it during teardown.
    Running that file first (alphabetically) leaves this file without
    an override unless we restore it here.
    """
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer
    yield
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_01_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /v1/api/reports/tests/{test_id}
# ---------------------------------------------------------------------------

def test_02_test_report_success():
    r = client.get("/v1/api/reports/tests/1")
    assert r.status_code == 200
    data = r.json()
    assert data["test_id"] == 1
    assert data["test_name"] == "Python Basics"
    assert data["attempt_count"] == 4
    assert data["avg_score"] is not None
    assert "score_distribution" in data
    assert isinstance(data["score_distribution"], dict)


def test_03_test_report_abandoned_excluded():
    r = client.get("/v1/api/reports/tests/1")
    data = r.json()
    # Only 4 COMPLETED sessions (s6 is ABANDONED — excluded)
    assert data["attempt_count"] == 4


def test_04_test_report_not_found():
    r = client.get("/v1/api/reports/tests/999")
    assert r.status_code == 404


def test_05_test_report_pass_rate():
    r = client.get("/v1/api/reports/tests/1")
    data = r.json()
    # Scores: 85 (pass), 62.5 (fail), 91 (pass), 45 (fail) → pass_rate = 2/4 = 0.5
    assert abs(data["pass_rate"] - 0.5) < 0.01


def test_06_test_report_score_distribution():
    r = client.get("/v1/api/reports/tests/1")
    data = r.json()
    dist = data["score_distribution"]
    assert dist["0-49"] == 1   # 45.0
    assert dist["50-69"] == 1  # 62.5
    assert dist["70-89"] == 1  # 85.0
    assert dist["90-100"] == 1 # 91.0


def test_07_test_report_empty_test():
    r = client.get("/v1/api/reports/tests/3")
    assert r.status_code == 200
    data = r.json()
    assert data["attempt_count"] == 0
    assert data["avg_score"] is None
    assert data["pass_rate"] is None


# ---------------------------------------------------------------------------
# GET /v1/api/reports/aggregate
# ---------------------------------------------------------------------------

def test_08_aggregate_success():
    r = client.get("/v1/api/reports/aggregate")
    assert r.status_code == 200
    data = r.json()
    assert data["total_tests"] == 4
    assert "tests" in data
    assert len(data["tests"]) <= 20


def test_09_aggregate_pagination():
    r = client.get("/v1/api/reports/aggregate?page=1&size=2")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tests"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


def test_10_aggregate_page_2():
    # 4 total tests, size=3 → page 1 has 3, page 2 has 1
    r = client.get("/v1/api/reports/aggregate?page=2&size=3")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tests"]) == 1


def test_11_aggregate_sort_by_name_asc():
    r = client.get("/v1/api/reports/aggregate?sort=test_name:asc")
    assert r.status_code == 200
    data = r.json()
    names = [t["test_name"] for t in data["tests"]]
    assert names == sorted(names)


def test_12_aggregate_sort_by_attempt_count():
    r = client.get("/v1/api/reports/aggregate?sort=attempt_count:desc")
    assert r.status_code == 200
    data = r.json()
    counts = [t["attempt_count"] for t in data["tests"]]
    assert counts == sorted(counts, reverse=True)


def test_13_aggregate_invalid_sort_falls_back():
    r = client.get("/v1/api/reports/aggregate?sort=invalid_column:desc")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /v1/api/reports/tests/{test_id}/rankings
# ---------------------------------------------------------------------------

def test_14_rankings_success():
    r = client.get("/v1/api/reports/tests/1/rankings")
    assert r.status_code == 200
    data = r.json()
    assert data["test_id"] == 1
    assert len(data["rankings"]) == 4


def test_15_rankings_ordered_by_score_desc():
    r = client.get("/v1/api/reports/tests/1/rankings")
    data = r.json()
    scores = [e["score"] for e in data["rankings"]]
    assert scores == sorted(scores, reverse=True)


def test_16_rankings_top_score():
    r = client.get("/v1/api/reports/tests/1/rankings")
    data = r.json()
    assert data["rankings"][0]["score"] == 91.0
    assert data["rankings"][0]["rank"] == 1


def test_17_rankings_pagination():
    r = client.get("/v1/api/reports/tests/1/rankings?page=1&size=2")
    assert r.status_code == 200
    data = r.json()
    assert len(data["rankings"]) == 2


def test_18_rankings_empty_test():
    r = client.get("/v1/api/reports/tests/3/rankings")
    assert r.status_code == 200
    data = r.json()
    assert data["rankings"] == []


# ---------------------------------------------------------------------------
# RBAC — now tests the JWT layer (require_role / verify_jwt)
# ---------------------------------------------------------------------------

def _token(role: str) -> str:
    from src.config.settings import settings as _s
    return _jwt.encode(
        {"sub": "1", "role": role, "exp": int(_time.time()) + 3600},
        _s.JWT_SECRET,
        algorithm="HS256",
    )


def test_19_rbac_participant_jwt_returns_403():
    app.dependency_overrides.pop(verify_jwt, None)
    r = client.get(
        "/v1/api/reports/tests/1",
        headers={"Authorization": f"Bearer {_token('PARTICIPANT')}"},
    )
    assert r.status_code == 403
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer


def test_20_rbac_no_token_returns_401():
    app.dependency_overrides.pop(verify_jwt, None)
    r = client.get("/v1/api/reports/tests/1")
    assert r.status_code == 401
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer


def test_21_rbac_trainer_jwt_accepted():
    app.dependency_overrides.pop(verify_jwt, None)
    r = client.get(
        "/v1/api/reports/tests/1",
        headers={"Authorization": f"Bearer {_token('TRAINER')}"},
    )
    assert r.status_code == 200
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer


def test_22_rbac_invalid_token_returns_401():
    app.dependency_overrides.pop(verify_jwt, None)
    r = client.get(
        "/v1/api/reports/tests/1",
        headers={"Authorization": "Bearer notavalidtoken"},
    )
    assert r.status_code == 401
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer


# ---------------------------------------------------------------------------
# GET /v1/api/reports/user/{user_id}
# ---------------------------------------------------------------------------



async def override_get_current_user_10():
    return {"id": 10, "role": "PARTICIPANT"}


async def override_get_current_trainer_as_user():
    return {"id": 1, "role": "TRAINER"}


# ---------------------------------------------------------------------------
# GET /v1/api/reports/user/{user_id}  — summary envelope
# ---------------------------------------------------------------------------

def test_23_user_summary_own():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == 10
    assert data["total_attempts"] == 2  # s1 (test1) + s5 (test2)
    assert data["avg_score"] is not None
    assert abs(data["avg_score"] - 81.5) < 0.1  # (85 + 78) / 2
    assert data["best_score"] == 85.0
    assert data["most_recent"] is not None
    assert data["most_recent"]["status"] == "COMPLETED"
    app.dependency_overrides.pop(get_current_user, None)


def test_24_user_summary_trainer_sees_any_user():
    app.dependency_overrides[get_current_user] = override_get_current_trainer_as_user
    r = client.get("/v1/api/reports/user/13")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == 13
    assert data["total_attempts"] == 1
    assert data["best_score"] == 45.0
    app.dependency_overrides.pop(get_current_user, None)


def test_25_user_summary_forbidden_wrong_user():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/99")
    assert r.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


def test_26_user_summary_empty_user():
    app.dependency_overrides[get_current_user] = override_get_current_trainer_as_user
    r = client.get("/v1/api/reports/user/999")
    assert r.status_code == 200
    data = r.json()
    assert data["total_attempts"] == 0
    assert data["avg_score"] is None
    assert data["best_score"] is None
    assert data["most_recent"] is None
    app.dependency_overrides.pop(get_current_user, None)


def test_27_user_summary_time_spent():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10")
    data = r.json()
    # user 10 has 2 sessions with started_at set — total time should be > 0
    assert data["total_time_spent_seconds"] is not None
    assert data["total_time_spent_seconds"] > 0
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /v1/api/reports/user/{user_id}/attempts  — paginated history
# ---------------------------------------------------------------------------

def test_28_user_attempts_all():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10/attempts")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == 10
    assert data["total"] == 2
    assert len(data["attempts"]) == 2
    app.dependency_overrides.pop(get_current_user, None)


def test_29_user_attempts_filter_by_test_id():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10/attempts?test_id=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["attempts"][0]["test_id"] == 1
    app.dependency_overrides.pop(get_current_user, None)


def test_30_user_attempts_filter_by_status_completed():
    app.dependency_overrides[get_current_user] = override_get_current_trainer_as_user
    # user 14 has 1 ABANDONED session — filter COMPLETED returns 0
    r = client.get("/v1/api/reports/user/14/attempts?status=COMPLETED")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["attempts"] == []
    app.dependency_overrides.pop(get_current_user, None)


def test_31_user_attempts_pagination():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10/attempts?page=1&size=1")
    assert r.status_code == 200
    data = r.json()
    assert len(data["attempts"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] == 2
    app.dependency_overrides.pop(get_current_user, None)


def test_32_user_attempts_sort_score_asc():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/10/attempts?sort=percentage_score:asc")
    assert r.status_code == 200
    data = r.json()
    scores = [a["percentage_score"] for a in data["attempts"] if a["percentage_score"] is not None]
    assert scores == sorted(scores)
    app.dependency_overrides.pop(get_current_user, None)


def test_33_user_attempts_forbidden_wrong_user():
    app.dependency_overrides[get_current_user] = override_get_current_user_10
    r = client.get("/v1/api/reports/user/99/attempts")
    assert r.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# median_score in test summary and aggregate
# ---------------------------------------------------------------------------

def test_34_test_report_median_score():
    r = client.get("/v1/api/reports/tests/1")
    data = r.json()
    # Scores: 45, 62.5, 85, 91 → sorted median = (62.5 + 85) / 2 = 73.75
    assert "median_score" in data
    assert abs(data["median_score"] - 73.75) < 0.01


def test_35_test_report_median_none_for_empty():
    r = client.get("/v1/api/reports/tests/3")
    data = r.json()
    assert data["median_score"] is None


def test_36_aggregate_includes_median_score():
    r = client.get("/v1/api/reports/aggregate")
    data = r.json()
    for test in data["tests"]:
        assert "median_score" in test


# ---------------------------------------------------------------------------
# GET /v1/api/reports/tests/{test_id}/questions  — per-question stats
# ---------------------------------------------------------------------------

def test_37_questions_stats_returns_data():
    r = client.get("/v1/api/reports/tests/4/questions")
    assert r.status_code == 200
    data = r.json()
    assert data["test_id"] == 4
    questions = {q["question_id"]: q for q in data["questions"]}
    # qA1: 2 attempts, 1 correct
    assert questions["qA1"]["attempt_count"] == 2
    assert questions["qA1"]["correct_count"] == 1
    assert abs(questions["qA1"]["correct_rate"] - 0.5) < 0.01
    # qB1: 1 attempt, 1 correct
    assert questions["qB1"]["attempt_count"] == 1
    assert questions["qB1"]["correct_count"] == 1
    assert questions["qB1"]["correct_rate"] == 1.0


def test_38_questions_stats_empty_test():
    r = client.get("/v1/api/reports/tests/3/questions")
    assert r.status_code == 200
    data = r.json()
    assert data["questions"] == []


def test_39_questions_stats_404_missing_test():
    r = client.get("/v1/api/reports/tests/999/questions")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# get_current_user now requires Bearer JWT (not X-User-* headers)
# ---------------------------------------------------------------------------

def test_40_user_endpoint_no_token_returns_401():
    # Remove all overrides so real auth runs
    app.dependency_overrides.pop(verify_jwt, None)
    app.dependency_overrides.pop(get_current_user, None)
    r = client.get("/v1/api/reports/user/10")
    assert r.status_code == 401
    app.dependency_overrides[verify_jwt] = override_verify_jwt_trainer
