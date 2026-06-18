from datetime import datetime, timedelta

from src.models.quiz_session import QuizSession, SessionStatus
from src.models.session_answer import SessionAnswer


def _session(idx, *, user_id=1, test_id=1, status=SessionStatus.SUBMITTED, score=None):
    base_dt = datetime(2024, 1, 1) + timedelta(days=idx)
    qs = QuizSession(
        id=f"sess-{idx:04d}",
        test_id=test_id,
        user_id=user_id,
        status=status,
        server_now=base_dt,
        submitted_at=base_dt + timedelta(hours=1)
        if status == SessionStatus.SUBMITTED
        else None,
        created_at=base_dt,
    )
    answers = []
    if score is not None:
        answers.append(SessionAnswer(session_id=f"sess-{idx:04d}", score=score))
    return qs, answers


def _seed(db, sessions_with_answers):
    for qs, answers in sessions_with_answers:
        db.add(qs)
        for a in answers:
            db.add(a)
    db.commit()


# ── summary endpoint ───────────────────────────────────────────────────────────


def test_summary_empty_user(client):
    resp = client.get("/v1/api/reports/user/999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 999
    assert data["total_attempts"] == 0
    assert data["avg_score"] is None
    assert data["best_score"] is None
    assert data["most_recent_attempt"] is None


def test_summary_aggregates(client, db):
    _seed(
        db,
        [
            _session(1, score=0.8),
            _session(2, score=0.6),
            _session(3, score=1.0),
        ],
    )
    resp = client.get("/v1/api/reports/user/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_attempts"] == 3
    assert abs(data["avg_score"] - (0.8 + 0.6 + 1.0) / 3) < 0.001
    assert abs(data["best_score"] - 1.0) < 0.001


def test_summary_excludes_non_submitted(client, db):
    _seed(
        db,
        [
            _session(1, score=0.9),
            _session(2, status=SessionStatus.IN_PROGRESS),
        ],
    )
    resp = client.get("/v1/api/reports/user/1")
    data = resp.json()
    assert data["total_attempts"] == 1


def test_summary_most_recent(client, db):
    _seed(
        db,
        [
            _session(1, score=0.5),
            _session(3, score=0.9),
            _session(2, score=0.7),
        ],
    )
    resp = client.get("/v1/api/reports/user/1")
    data = resp.json()
    # session 3 has the latest submitted_at (day 3 + 1h)
    assert data["most_recent_attempt"]["session_id"] == "sess-0003"
    assert abs(data["most_recent_attempt"]["score"] - 0.9) < 0.001


def test_summary_total_time_not_negative(client, db):
    _seed(db, [_session(1, score=0.5)])
    resp = client.get("/v1/api/reports/user/1")
    data = resp.json()
    tts = data["total_time_spent_seconds"]
    # PG returns a positive value; SQLite returns None — both are acceptable
    assert tts is None or tts >= 0


# ── attempts endpoint ──────────────────────────────────────────────────────────


def test_attempts_pagination(client, db):
    _seed(db, [_session(i, score=float(i) / 25) for i in range(1, 26)])

    resp = client.get("/v1/api/reports/user/1/attempts?page=1&size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert data["page"] == 1
    assert data["size"] == 20

    resp2 = client.get("/v1/api/reports/user/1/attempts?page=2&size=20")
    data2 = resp2.json()
    assert len(data2["items"]) == 5


def test_attempts_default_pagination(client, db):
    _seed(db, [_session(i) for i in range(1, 6)])
    resp = client.get("/v1/api/reports/user/1/attempts")
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["size"] == 20


def test_attempts_filter_test_id(client, db):
    _seed(
        db,
        [
            _session(1, test_id=1),
            _session(2, test_id=2),
            _session(3, test_id=1),
        ],
    )
    resp = client.get("/v1/api/reports/user/1/attempts?test_id=1")
    data = resp.json()
    assert data["total"] == 2
    assert all(item["test_id"] == 1 for item in data["items"])


def test_attempts_filter_status(client, db):
    _seed(
        db,
        [
            _session(1, status=SessionStatus.SUBMITTED),
            _session(2, status=SessionStatus.IN_PROGRESS),
            _session(3, status=SessionStatus.SUBMITTED),
        ],
    )
    resp = client.get("/v1/api/reports/user/1/attempts?status=SUBMITTED")
    data = resp.json()
    assert data["total"] == 2
    assert all(item["status"] == "SUBMITTED" for item in data["items"])


def test_attempts_filter_date_range(client, db):
    _seed(
        db,
        [
            _session(1),  # submitted 2024-01-01 + 1h
            _session(5),  # submitted 2024-01-05 + 1h
            _session(10),  # submitted 2024-01-10 + 1h
        ],
    )
    resp = client.get("/v1/api/reports/user/1/attempts?from=2024-01-04&to=2024-01-09")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["session_id"] == "sess-0005"


def test_attempts_sort_created_at_asc(client, db):
    _seed(db, [_session(i) for i in range(1, 4)])
    resp = client.get("/v1/api/reports/user/1/attempts?sort=created_at:asc")
    data = resp.json()
    ids = [item["session_id"] for item in data["items"]]
    assert ids == sorted(ids)


def test_attempts_sort_invalid_field(client, db):
    resp = client.get("/v1/api/reports/user/1/attempts?sort=bad_field:desc")
    assert resp.status_code == 400


def test_attempts_size_max_capped(client, db):
    _seed(db, [_session(i) for i in range(1, 6)])
    # size > 100 should be rejected by the validator (ge=1, le=100)
    resp = client.get("/v1/api/reports/user/1/attempts?size=200")
    assert resp.status_code == 422


def test_attempts_includes_score(client, db):
    _seed(db, [_session(1, score=0.75)])
    resp = client.get("/v1/api/reports/user/1/attempts")
    data = resp.json()
    assert abs(data["items"][0]["score"] - 0.75) < 0.001


def test_attempts_empty_user(client):
    resp = client.get("/v1/api/reports/user/999/attempts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
