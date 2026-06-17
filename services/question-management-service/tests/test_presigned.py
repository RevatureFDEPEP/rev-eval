"""Unit tests for the question-image presigned-upload feature (W2-F5).

SYNC only — the async auth coroutines are driven with `asyncio.run`, boto3 is
mocked, and nothing imports the route module / models, so the suite needs only
pytest + the service requirements (no TestClient, no live MinIO or Mongo):
- service-level tests mock `generate_presigned_post` / `ensure_bucket` so the
  pure helper is exercised without any network call;
- the upload now mints a presigned POST policy (not a PUT URL) so a
  `content-length-range` condition can cap the object size server-side;
- auth-dependency tests call the dependencies directly and assert the auth matrix
  (401 missing identity, 403 wrong role, trainer pass).
"""

import asyncio

import pytest
from fastapi import HTTPException
from src.services import upload_service
from src.services.upload_service import (
    ALLOWED_CONTENT_TYPES,
    InvalidContentTypeError,
    InvalidFilenameError,
    build_object_key,
    create_presigned_upload,
)
from src.utils.auth import get_current_trainer, get_current_user_from_headers

# 5 MiB — must match s3_client.MAX_UPLOAD_BYTES (the server-enforced cap).
MAX_BYTES = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Service-level unit tests (pure helper, S3 mocked)
# ---------------------------------------------------------------------------


def _fake_presigner(captured):
    """Stub for generate_presigned_post recording kwargs + returning boto3 shape.

    Mirrors boto3's ``generate_presigned_post`` return: ``{"url", "fields"}``.
    The signed policy fields normally include the Content-Type and the encoded
    policy/signature; the stub returns just enough to exercise the contract.
    """

    def _gen(*, key, content_type, expires_in, max_bytes):
        captured.update(
            key=key,
            content_type=content_type,
            expires_in=expires_in,
            max_bytes=max_bytes,
        )
        return {
            "url": "https://minio.local/question-images",
            "fields": {
                "key": key,
                "Content-Type": content_type,
                "policy": "fake-base64-policy",
                "x-amz-signature": "fakesig",
            },
        }

    return _gen


def test_create_presigned_upload_returns_post_contract(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        upload_service.s3_client,
        "generate_presigned_post",
        _fake_presigner(captured),
    )
    monkeypatch.setattr(upload_service.s3_client, "ensure_bucket", lambda *a, **k: None)

    result = create_presigned_upload("diagram.png", "image/png")

    # Presigned POST contract: url + fields + key + expires_in + max_bytes.
    assert set(result) == {"url", "fields", "key", "expires_in", "max_bytes"}
    assert result["key"].startswith("questions/")
    assert result["key"].endswith("/diagram.png")
    assert result["url"].startswith("https://")
    # `fields` is the multipart form-data the client must POST before the file.
    assert isinstance(result["fields"], dict)
    assert result["fields"]["Content-Type"] == "image/png"
    assert isinstance(result["expires_in"], int) and result["expires_in"] > 0
    # The 5 MiB cap is surfaced to the client and enforced server-side.
    assert result["max_bytes"] == MAX_BYTES
    # the helper passed the validated content_type + cap through to the signer
    assert captured["content_type"] == "image/png"
    assert captured["key"] == result["key"]
    assert captured["max_bytes"] == MAX_BYTES


def test_max_bytes_cap_is_5_mib():
    """The server-enforced ceiling must be exactly 5 MiB."""
    assert upload_service.s3_client.MAX_UPLOAD_BYTES == 5 * 1024 * 1024


def test_presigned_post_binds_content_length_range(monkeypatch):
    """The real signer must set a content-length-range condition capped at 5 MiB.

    Exercises s3_client.generate_presigned_post against a stub boto3 client so
    the Conditions list is asserted without any network/MinIO.
    """
    captured: dict = {}

    class _StubBoto:
        def generate_presigned_post(self, **kwargs):
            captured.update(kwargs)
            return {"url": "https://minio.local/question-images", "fields": {}}

    monkeypatch.setattr(upload_service.s3_client, "s3_client", _StubBoto())

    upload_service.s3_client.generate_presigned_post(
        key="questions/abc/diagram.png",
        content_type="image/png",
    )

    conditions = captured["Conditions"]
    assert ["content-length-range", 1, MAX_BYTES] in conditions
    assert {"Content-Type": "image/png"} in conditions
    assert captured["Fields"]["Content-Type"] == "image/png"


def test_create_presigned_upload_calls_ensure_bucket(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(
        upload_service.s3_client,
        "generate_presigned_post",
        _fake_presigner({}),
    )

    def _ensure(*a, **k):
        calls["n"] += 1

    monkeypatch.setattr(upload_service.s3_client, "ensure_bucket", _ensure)

    create_presigned_upload("p.jpg", "image/jpeg")
    assert calls["n"] == 1


def test_ensure_bucket_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(
        upload_service.s3_client, "generate_presigned_post", _fake_presigner({})
    )

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("ensure_bucket should not be called")

    monkeypatch.setattr(upload_service.s3_client, "ensure_bucket", _boom)

    result = create_presigned_upload("p.png", "image/png", ensure_bucket=False)
    assert result["key"].endswith("/p.png")


@pytest.mark.parametrize(
    "bad_type",
    ["application/pdf", "image/gif", "text/plain", "image/svg+xml", ""],
)
def test_disallowed_content_type_rejected(bad_type, monkeypatch):
    monkeypatch.setattr(upload_service.s3_client, "ensure_bucket", lambda *a, **k: None)
    monkeypatch.setattr(
        upload_service.s3_client,
        "generate_presigned_post",
        _fake_presigner({}),
    )
    with pytest.raises(InvalidContentTypeError):
        create_presigned_upload("x.png", bad_type)


@pytest.mark.parametrize("good_type", sorted(ALLOWED_CONTENT_TYPES))
def test_allowed_content_types_accepted(good_type, monkeypatch):
    monkeypatch.setattr(upload_service.s3_client, "ensure_bucket", lambda *a, **k: None)
    monkeypatch.setattr(
        upload_service.s3_client,
        "generate_presigned_post",
        _fake_presigner({}),
    )
    result = create_presigned_upload("img", good_type)
    assert result["key"].startswith("questions/")


def test_object_key_is_unique_per_call():
    k1 = build_object_key("same.png")
    k2 = build_object_key("same.png")
    assert k1 != k2
    assert k1.endswith("/same.png") and k2.endswith("/same.png")


def test_filename_is_sanitized_against_path_traversal():
    key = build_object_key("../../etc/passwd")
    # directory components are stripped; only the basename survives
    assert key.endswith("/passwd")
    assert ".." not in key


@pytest.mark.parametrize("bad_name", ["", "   ", "/", ".", "..", "/../"])
def test_empty_or_unusable_filename_rejected(bad_name):
    with pytest.raises(InvalidFilenameError):
        build_object_key(bad_name)


# ---------------------------------------------------------------------------
# Auth dependency tests (called directly, no app/TestClient/httpx)
# ---------------------------------------------------------------------------


def test_missing_identity_headers_401():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_current_user_from_headers(
                x_user_id=None, x_user_email=None, x_user_role=None
            )
        )
    assert exc.value.status_code == 401


def test_identity_resolved_from_headers():
    user = asyncio.run(
        get_current_user_from_headers(
            x_user_id="u-1", x_user_email=None, x_user_role="TRAINER"
        )
    )
    assert user == {"id": "u-1", "email": None, "role": "TRAINER"}


def test_trainer_gate_allows_trainer():
    user = {"id": "u-1", "email": None, "role": "TRAINER"}
    assert asyncio.run(get_current_trainer(current_user=user)) is user


def test_trainer_gate_is_case_insensitive():
    user = {"id": "u-1", "email": None, "role": "trainer"}
    assert asyncio.run(get_current_trainer(current_user=user)) is user


@pytest.mark.parametrize("role", ["PARTICIPANT", "ADMIN", None, ""])
def test_trainer_gate_rejects_non_trainer_403(role):
    user = {"id": "u-2", "email": None, "role": role}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_trainer(current_user=user))
    assert exc.value.status_code == 403
