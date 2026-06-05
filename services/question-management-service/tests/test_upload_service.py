"""Unit tests for the pre-signed upload service.

No Mongo or MinIO required — generate_presigned_put_url is patched so these
cover content-type validation, server-side key generation, and the response
shape only.
"""
import re
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from src.config.settings import settings
from src.services.upload_service import ALLOWED_IMAGE_TYPES, UploadService

KEY_PATTERN = re.compile(r"^questions/[0-9a-f]{32}\.(png|jpg)$")


@patch("src.services.upload_service.generate_presigned_put_url", return_value="http://signed-url")
def test_png_upload_response_shape(mock_presign):
    result = UploadService.presigned_question_image_upload("image/png")

    assert result["upload_url"] == "http://signed-url"
    assert result["expires_in"] == settings.S3_PRESIGN_EXPIRY_SECONDS
    assert KEY_PATTERN.match(result["object_key"])
    assert result["object_key"].endswith(".png")
    mock_presign.assert_called_once_with(
        key=result["object_key"], content_type="image/png"
    )


@patch("src.services.upload_service.generate_presigned_put_url", return_value="http://signed-url")
def test_jpeg_maps_to_jpg_extension(mock_presign):
    result = UploadService.presigned_question_image_upload("image/jpeg")

    assert KEY_PATTERN.match(result["object_key"])
    assert result["object_key"].endswith(".jpg")


@patch("src.services.upload_service.generate_presigned_put_url", return_value="http://signed-url")
def test_keys_are_unique_per_call(mock_presign):
    first = UploadService.presigned_question_image_upload("image/png")
    second = UploadService.presigned_question_image_upload("image/png")
    assert first["object_key"] != second["object_key"]


@pytest.mark.parametrize("content_type", ["application/pdf", "image/gif", "image/svg+xml", "", "png"])
def test_unsupported_content_type_rejected(content_type):
    with pytest.raises(HTTPException) as exc_info:
        UploadService.presigned_question_image_upload(content_type)
    assert exc_info.value.status_code == 400


def test_allowed_types_are_png_and_jpeg_only():
    assert set(ALLOWED_IMAGE_TYPES) == {"image/png", "image/jpeg"}
