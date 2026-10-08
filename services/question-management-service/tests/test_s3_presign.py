"""Presigned image URLs must point at the browser-facing storage origin.

Regression: URLs were signed for the Compose-internal host ``minio:9000``,
which the browser cannot resolve. SigV4 signs the Host header, so the URL has
to be generated for the public origin rather than rewritten afterwards.
Presigning is an offline computation, so no MinIO is needed here.
"""
import importlib
import os
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("PORT", "8003")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

import src.config.settings as settings_module  # noqa: E402
import src.utils.s3_client as s3_module  # noqa: E402


def _reload_with_env(env: dict):
    with patch.dict(os.environ, env):
        importlib.reload(settings_module)
        return importlib.reload(s3_module)


def teardown_module():
    importlib.reload(settings_module)
    importlib.reload(s3_module)


class TestPresignedUrlHost:
    def test_public_endpoint_is_used_for_browser_urls(self):
        s3 = _reload_with_env(
            {"S3_ENDPOINT_URL": "http://minio:9000", "S3_PUBLIC_ENDPOINT_URL": "https://localhost"}
        )
        parts = urlsplit(s3.generate_presigned_get_url("questions/abc/image"))
        assert (parts.scheme, parts.netloc) == ("https", "localhost")
        # Path-style, so a single /<bucket>/ proxy location can serve it.
        assert parts.path == "/question-images/questions/abc/image"
        query = parse_qs(parts.query)
        assert query["X-Amz-SignedHeaders"] == ["host"]
        assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]

    def test_upload_url_uses_public_endpoint(self):
        s3 = _reload_with_env(
            {"S3_ENDPOINT_URL": "http://minio:9000", "S3_PUBLIC_ENDPOINT_URL": "https://eval.example.com"}
        )
        url = s3.generate_presigned_put_url("questions/abc/image", content_type="image/png")
        parts = urlsplit(url)
        assert parts.netloc == "eval.example.com"
        assert parts.path == "/question-images/questions/abc/image"

    def test_internal_client_keeps_private_endpoint(self):
        s3 = _reload_with_env(
            {"S3_ENDPOINT_URL": "http://minio:9000", "S3_PUBLIC_ENDPOINT_URL": "https://localhost"}
        )
        assert s3.s3_client.meta.endpoint_url == "http://minio:9000"
        assert s3.presign_client.meta.endpoint_url == "https://localhost"

    def test_falls_back_to_internal_endpoint_when_public_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "S3_PUBLIC_ENDPOINT_URL"}
        env["S3_ENDPOINT_URL"] = "http://minio:9000"
        with patch.dict(os.environ, env, clear=True):
            importlib.reload(settings_module)
            s3 = importlib.reload(s3_module)
        parts = urlsplit(s3.generate_presigned_get_url("k", bucket_name="other"))
        assert parts.netloc == "minio:9000"
        assert parts.path == "/other/k"
