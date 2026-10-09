"""
Who may read the question bank, and who may see answer keys.

Every endpoint needs a caller. The question bank (every read route and image
download URLs) is for trainers and for test-management-service (internal
token), which needs correct_answers to score submissions. A participant gets
403 and the bank is not queried: participants receive their own quiz
session's questions from test-management-service, without answer keys.
Image upload is trainer-only. The development placeholder internal token
works only with APP_ENV=development.

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
from pydantic import ValidationError  # noqa: E402
from src.config.settings import DEV_INTERNAL_SERVICE_TOKEN, Settings  # noqa: E402

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
                c.mocks = mocks
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


@pytest.mark.parametrize("path,method", READ_ROUTES)
def test_participant_cannot_read_the_question_bank(client, path, method):
    resp = client.get(path, headers=_bearer("PARTICIPANT"))
    assert resp.status_code == 403
    assert "question_text" not in resp.text
    client.mocks[method].assert_not_awaited()


@pytest.mark.parametrize("path,method", READ_ROUTES)
def test_unknown_role_cannot_read_the_question_bank(client, path, method):
    assert client.get(path, headers=_bearer("GUEST")).status_code == 403
    client.mocks[method].assert_not_awaited()


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_trainer_reads_questions_with_answer_keys(client, path, _):
    resp = client.get(path, headers=_bearer("TRAINER"))
    assert resp.status_code == 200
    mcq = next(i for i in _items(resp) if i["type"] == "mcq")
    assert mcq["question_text"] == _MCQ["question_text"]
    assert mcq["options"] == _MCQ["options"]
    assert mcq["correct_answers"] == [2]
    assert mcq["answer_explanation"] == "Two and two make four."


@pytest.mark.parametrize("path,_", READ_ROUTES)
def test_internal_service_gets_answer_keys(client, path, _):
    resp = client.get(path, headers={"X-Internal-Service-Token": INTERNAL})
    assert resp.status_code == 200
    mcq = next(i for i in _items(resp) if i["type"] == "mcq")
    assert mcq["correct_answers"] == [2]


def test_trainer_sees_sample_answer(client):
    trainer = client.get("/v1/api/questions/", headers=_bearer("TRAINER")).json()
    assert next(q for q in trainer if q["type"] == "text")["sample_answer"] == "A function that calls itself."


def test_wrong_internal_token_alone_is_401(client):
    resp = client.get("/v1/api/questions/", headers={"X-Internal-Service-Token": "guess"})
    assert resp.status_code == 401


def test_wrong_internal_token_with_participant_jwt_is_a_participant(client):
    headers = {**_bearer("PARTICIPANT"), "X-Internal-Service-Token": "guess"}
    resp = client.get("/v1/api/questions/", headers=headers)
    assert resp.status_code == 403
    client.mocks["get_all_questions"].assert_not_awaited()


@pytest.mark.parametrize("configured", [None, "", "   "])
def test_internal_token_ignored_when_not_configured(client, configured):
    with patch.object(deps.settings, "INTERNAL_SERVICE_TOKEN", configured):
        resp = client.get("/v1/api/questions/", headers={"X-Internal-Service-Token": INTERNAL})
        assert resp.status_code == 401
        resp = client.get("/v1/api/questions/", headers={"X-Internal-Service-Token": configured or ""})
        assert resp.status_code == 401
        resp = client.get(
            "/v1/api/questions/", headers={**_bearer("PARTICIPANT"), "X-Internal-Service-Token": ""}
        )
        assert resp.status_code == 403
    client.mocks["get_all_questions"].assert_not_awaited()


class TestDevelopmentPlaceholderToken:
    """The placeholder from .env.example works only with APP_ENV=development."""

    def test_placeholder_refused_outside_development(self, client):
        with patch.object(deps.settings, "INTERNAL_SERVICE_TOKEN", DEV_INTERNAL_SERVICE_TOKEN), \
                patch.object(deps.settings, "APP_ENV", "production"):
            resp = client.get(
                "/v1/api/questions/", headers={"X-Internal-Service-Token": DEV_INTERNAL_SERVICE_TOKEN}
            )
        assert resp.status_code == 401
        client.mocks["get_all_questions"].assert_not_awaited()

    def test_placeholder_accepted_in_development(self, client):
        with patch.object(deps.settings, "INTERNAL_SERVICE_TOKEN", DEV_INTERNAL_SERVICE_TOKEN), \
                patch.object(deps.settings, "APP_ENV", "development"):
            resp = client.get(
                "/v1/api/questions/", headers={"X-Internal-Service-Token": DEV_INTERNAL_SERVICE_TOKEN}
            )
        assert resp.status_code == 200
        assert next(i for i in resp.json() if i["type"] == "mcq")["correct_answers"] == [2]

    def test_service_refuses_to_start_with_placeholder_outside_development(self):
        with pytest.raises(ValidationError, match="development placeholder"):
            Settings(SERVICE_NAME="qm", INTERNAL_SERVICE_TOKEN=DEV_INTERNAL_SERVICE_TOKEN, APP_ENV="production")

    def test_service_starts_with_placeholder_in_development(self):
        s = Settings(SERVICE_NAME="qm", INTERNAL_SERVICE_TOKEN=DEV_INTERNAL_SERVICE_TOKEN, APP_ENV="development")
        assert s.internal_service_token == DEV_INTERNAL_SERVICE_TOKEN

    def test_real_token_is_used_in_any_environment(self):
        s = Settings(SERVICE_NAME="qm", INTERNAL_SERVICE_TOKEN="  a-long-random-value  ", APP_ENV="production")
        assert s.internal_service_token == "a-long-random-value"

    @pytest.mark.parametrize("value", [None, "", "  "])
    def test_unset_token_is_never_used(self, value):
        assert Settings(SERVICE_NAME="qm", INTERNAL_SERVICE_TOKEN=value).internal_service_token is None


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

    def test_participant_cannot_get_download_url(self, client):
        with patch(f"{ROUTES}.generate_presigned_get_url") as presign:
            resp = client.get(
                f"/v1/api/questions/{_MCQ['_id']}/image/download-url", headers=_bearer("PARTICIPANT")
            )
        assert resp.status_code == 403
        presign.assert_not_called()
        client.mocks["get_question_by_id"].assert_not_awaited()

    @pytest.mark.parametrize("headers", [
        pytest.param(lambda: _bearer("TRAINER"), id="trainer"),
        pytest.param(lambda: {"X-Internal-Service-Token": INTERNAL}, id="internal"),
    ])
    def test_trainer_and_internal_service_get_download_url(self, client, headers):
        with patch(f"{ROUTES}.generate_presigned_get_url", return_value="https://s3/get"):
            resp = client.get(f"/v1/api/questions/{_MCQ['_id']}/image/download-url", headers=headers())
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://s3/get"
