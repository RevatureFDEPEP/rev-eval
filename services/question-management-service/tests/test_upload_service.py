"""Unit tests for UploadService pre-signed question-image uploads.

Pure presigning logic — no MinIO connection. boto3 signs offline, so these
run without any live S3/MinIO endpoint.
"""
import pytest
from fastapi import HTTPException

from src.config.settings import settings
from src.services.upload_service import ALLOWED_IMAGE_TYPES, UploadService


@pytest.mark.parametrize("content_type,ext", [
    ("image/png", "png"),
    ("image/jpeg", "jpg"),
])
def test_object_key_shape_and_extension(content_type, ext):
    result = UploadService.presigned_question_image_upload(content_type)
    key = result["object_key"]
    assert key.startswith("questions/")
    assert key.endswith(f".{ext}")
    # questions/<32-hex>.<ext>
    hexpart = key[len("questions/"):-(len(ext) + 1)]
    assert len(hexpart) == 32
    assert all(c in "0123456789abcdef" for c in hexpart)


def test_keys_are_unique_across_calls():
    keys = {
        UploadService.presigned_question_image_upload("image/png")["object_key"]
        for _ in range(50)
    }
    assert len(keys) == 50


@pytest.mark.parametrize("bad_type", [
    "image/gif", "image/webp", "application/pdf", "text/plain", "", "png",
])
def test_unsupported_content_type_rejected(bad_type):
    with pytest.raises(HTTPException) as exc:
        UploadService.presigned_question_image_upload(bad_type)
    assert exc.value.status_code == 400


def test_response_shape():
    result = UploadService.presigned_question_image_upload("image/png")
    assert set(result) == {"url", "fields", "object_key", "max_bytes", "expires_in"}
    assert isinstance(result["url"], str) and result["url"]
    assert isinstance(result["fields"], dict)
    assert result["max_bytes"] == settings.S3_MAX_UPLOAD_BYTES
    assert result["expires_in"] == settings.S3_PRESIGN_EXPIRY_SECONDS


def test_policy_fields_include_content_type_and_key():
    result = UploadService.presigned_question_image_upload("image/png")
    fields = result["fields"]
    assert fields.get("Content-Type") == "image/png"
    # boto3 echoes the object key into the POST form fields.
    assert fields.get("key") == result["object_key"]


def test_allowed_types_map_is_png_and_jpeg_only():
    assert ALLOWED_IMAGE_TYPES == {"image/png": "png", "image/jpeg": "jpg"}
