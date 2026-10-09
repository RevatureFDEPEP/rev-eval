"""
Who may see answer keys, and who may call the question endpoints at all.

Every endpoint needs a caller. Read endpoints serve trainers and participants,
but correct_answers, sample_answer and answer_explanation go only to trainers
and to test-management-service (internal token), which scores submissions.
A participant gets the question without them. Image upload is trainer-only.

QuestionService is mocked, so no MongoDB is needed.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("JWT_SECRET", "test-secret")

import time  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import src.utils.dependencies as deps  # noqa: E402
from main import app  # noqa: E402

ROUTES = "src.v1.routes.question_routes"
INTERNAL = "internal-test-token"
ANSWER_FIELDS = ("correct_answers", "sample_answer", "answer_explanation")


class _Doc:
    """Stand-in for a Beanie Question document."""

    def __init__(self, data):
        self._data = data

    def model_dump(self, **_):
        return dict(self._data)


_MCQ = {
    "_id": "507f1f77bcf86cd799439011", "type": "mcq", "question_text": "What is 2 + 2?",
    "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}],
    "correct_answers": [2], "sample_answer": None, "answer_explanation": "Two and two make four.",
    "difficulty": "easy", "skills": ["Math"], "tags": ["arithmetic"],
    "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
}
_TEXT = {
    "_id": "507f1f77bcf86cd799439012", "type": "text", "question_text": "Explain recursion.",
    "options": None, "correct_answers": None, "sample_answer": "A function that calls itself.",
    "answer_explanation": None, "difficulty": "medium", "skills": ["Python"], "tags": [],
    "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
}
_DOCS = [_Doc(_MCQ), _Doc(_TEXT)]

# (path, service method it calls)
READ_ROUTES = [
    ("/v1/api/questions/", "get_all_questions"),
    ("/v1/api/questions/by-tags?tags=arithmetic", "find_by_tags"),
    ("/v1/api/questions/filter?difficulty=easy", "filter_questions"),
    ("/v1/api/questions/by-type/mcq", "find_by_type"),
    ("/v1/api/questions/by-skill/Math", "find_by_skill"),
    ("/v1/api/questions/by-difficulty/easy", "find_by_difficulty"),
    (f"/v1/api/questions/{_MCQ['_id']}", "get_question_by_id"),
]


def _token(role, secret=None):
    return jwt.encode(
        {"sub": "7", "role": role, "email": f"{role.lower()}@example.com", "exp": int(time.time()) + 3600},
        secret or deps.settings.JWT_SECRET,
        algorithm="HS256",
    )


def _bearer(role):
    return {"Authorization": f"Bearer {_token(role)}"}


@pytest.fixture
def client():
    mocks = {
        name: AsyncMock(return_value=_DOCS[0] if name == "get_question_by_id" else _DOCS)
        for _, name in READ_ROUTES
    }
    with patch("main.init_db", new_callable=AsyncMock), \
            patch.object(deps.settings, "INTERNAL_SERVICE_TOKEN", INTERNAL):
        patches = [patch(f"{ROUTES}.QuestionService.{name}", mock) for name, mock in mocks.items()]
        for p in patches:
            p.start()
        try:
            with TestClient(app) as c:
                yield c
        finally:
            for p in patches:
                p.stop()


def _items(resp):
    body = resp.json()
    return body if isinstance(body, list) else [body]


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_read_without_token_is_401(client, path, _):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_read_with_invalid_token_is_401(client, path, _):
    bad = {"Authorization": f"Bearer {_token('PARTICIPANT', secret='not-the-secret')}"}
    assert client.get(path, headers=bad).status_code == 401


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_participant_gets_questions_without_answer_keys(client, path, _):
    resp = client.get(path, headers=_bearer("PARTICIPANT"))
    assert resp.status_code == 200
    for item in _items(resp):
        for field in ANSWER_FIELDS:
            assert field not in item
        assert item["question_text"] and item["_id"]
    mcq = next(i for i in _items(resp) if i["type"] == "mcq")
    assert mcq["options"] == _MCQ["options"]


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_trainer_gets_answer_keys(client, path, _):
    resp = client.get(path, headers=_bearer("TRAINER"))
    assert resp.status_code == 200
    mcq = next(i for i in _items(resp) if i["type"] == "mcq")
    assert mcq["correct_answers"] == [2]
    assert mcq["answer_explanation"] == "Two and two make four."


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_internal_service_gets_answer_keys(client, path, _):
    resp = client.get(path, headers={"X-Internal-Service-Token": INTERNAL})
    assert resp.status_code == 200
    mcq = next(i for i in _items(resp) if i["type"] == "mcq")
    assert mcq["correct_answers"] == [2]


def test_sample_answer_hidden_from_participant_and_shown_to_trainer(client):
    participant = client.get("/v1/api/questions/", headers=_bearer("PARTICIPANT")).json()
    trainer = client.get("/v1/api/questions/", headers=_bearer("TRAINER")).json()
    assert "sample_answer" not in next(q for q in participant if q["type"] == "text")
    assert next(q for q in trainer if q["type"] == "text")["sample_answer"] == "A function that calls itself."


def test_wrong_internal_token_alone_is_401(client):
    resp = client.get("/v1/api/questions/", headers={"X-Internal-Service-Token": "guess"})
    assert resp.status_code == 401


def test_wrong_internal_token_with_participant_jwt_is_a_participant(client):
    headers = {**_bearer("PARTICIPANT"), "X-Internal-Service-Token": "guess"}
    resp = client.get("/v1/api/questions/", headers=headers)
    assert resp.status_code == 200
    assert all("correct_answers" not in q for q in resp.json())


def test_internal_token_ignored_when_not_configured(client):
    with patch.object(deps.settings, "INTERNAL_SERVICE_TOKEN", None):
        resp = client.get("/v1/api/questions/", headers={"X-Internal-Service-Token": INTERNAL})
        assert resp.status_code == 401
        resp = client.get(
            "/v1/api/questions/", headers={**_bearer("PARTICIPANT"), "X-Internal-Service-Token": ""}
        )
        assert all("correct_answers" not in q for q in resp.json())


class TestImageRoutes:
    def test_upload_url_requires_a_token(self, client):
        assert client.post(f"/v1/api/questions/{_MCQ['_id']}/image/upload-url").status_code == 401

    def test_participant_cannot_get_upload_url(self, client):
        with patch(f"{ROUTES}.generate_presigned_put_url") as presign, patch(f"{ROUTES}.ensure_bucket"):
            resp = client.post(
                f"/v1/api/questions/{_MCQ['_id']}/image/upload-url", headers=_bearer("PARTICIPANT")
            )
        assert resp.status_code == 403
        presign.assert_not_called()

    def test_internal_token_cannot_get_upload_url(self, client):
        with patch(f"{ROUTES}.generate_presigned_put_url") as presign, patch(f"{ROUTES}.ensure_bucket"):
            resp = client.post(
                f"/v1/api/questions/{_MCQ['_id']}/image/upload-url",
                headers={"X-Internal-Service-Token": INTERNAL},
            )
        assert resp.status_code == 401
        presign.assert_not_called()

    def test_trainer_gets_upload_url(self, client):
        with patch(f"{ROUTES}.generate_presigned_put_url", return_value="https://s3/put") as presign, \
                patch(f"{ROUTES}.ensure_bucket"):
            resp = client.post(
                f"/v1/api/questions/{_MCQ['_id']}/image/upload-url", headers=_bearer("TRAINER")
            )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://s3/put"
        presign.assert_called_once()

    def test_download_url_requires_a_token(self, client):
        assert client.get(f"/v1/api/questions/{_MCQ['_id']}/image/download-url").status_code == 401

    def test_signed_in_user_gets_download_url(self, client):
        with patch(f"{ROUTES}.generate_presigned_get_url", return_value="https://s3/get"):
            resp = client.get(
                f"/v1/api/questions/{_MCQ['_id']}/image/download-url", headers=_bearer("PARTICIPANT")
            )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://s3/get"
