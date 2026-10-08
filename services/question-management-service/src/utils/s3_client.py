"""
S3-compatible object storage client (targets MinIO in local-first deploys).

Two boto3 clients share one configuration:

- ``s3_client`` talks to storage from inside the service (bucket checks) through
  ``S3_ENDPOINT_URL``, e.g. ``http://minio:9000`` on the Compose network.
- ``presign_client`` only signs URLs that are handed to the browser. It uses
  ``S3_PUBLIC_ENDPOINT_URL`` when set, because a SigV4 signature covers the
  Host header: a URL signed for ``minio:9000`` is neither reachable from the
  browser nor valid if rewritten to another host afterwards.

Path-style addressing keeps the bucket in the path (``/<bucket>/<key>``), so a
single reverse-proxy location can route it to MinIO.
"""
from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.config.settings import settings

logger = logging.getLogger(__name__)


def _build_client(endpoint_url: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


s3_client = _build_client(settings.S3_ENDPOINT_URL)
presign_client = _build_client(settings.S3_PUBLIC_ENDPOINT_URL or settings.S3_ENDPOINT_URL)


def ensure_bucket(bucket_name: Optional[str] = None) -> None:  # pragma: no cover
    """Create the configured bucket if it doesn't already exist."""
    name = bucket_name or settings.S3_BUCKET_NAME
    try:
        s3_client.head_bucket(Bucket=name)
        return
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code")
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    s3_client.create_bucket(Bucket=name)
    logger.info("Created S3 bucket %s", name)


def generate_presigned_put_url(
    key: str,
    content_type: str = "application/octet-stream",
    expires_in: Optional[int] = None,
    bucket_name: Optional[str] = None,
) -> str:
    """Generate a pre-signed URL that clients can PUT directly to."""
    return presign_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket_name or settings.S3_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in or settings.S3_PRESIGN_EXPIRY_SECONDS,
    )


def generate_presigned_get_url(
    key: str,
    expires_in: Optional[int] = None,
    bucket_name: Optional[str] = None,
) -> str:
    """Generate a pre-signed URL for read-only access to an existing object."""
    return presign_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket_name or settings.S3_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=expires_in or settings.S3_PRESIGN_EXPIRY_SECONDS,
    )
