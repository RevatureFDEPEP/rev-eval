"""
S3-compatible object storage client (targets MinIO in local-first deploys).

Provides a thin wrapper around boto3 configured with an explicit endpoint_url
so the same code works against AWS S3 or a local MinIO container.

W2 D8 candidate task: wire this into a question-image upload endpoint
(POST /v1/api/questions/{id}/image → returns pre-signed PUT URL).
"""
from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.config.settings import settings

logger = logging.getLogger(__name__)


def _build_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


s3_client = _build_client()


def ensure_bucket(bucket_name: Optional[str] = None) -> None:
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
    return s3_client.generate_presigned_url(
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
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket_name or settings.S3_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=expires_in or settings.S3_PRESIGN_EXPIRY_SECONDS,
    )
