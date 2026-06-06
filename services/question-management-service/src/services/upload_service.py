"""
Business logic for direct-to-MinIO question image uploads.

Stateless presigning only — no repository layer needed. The browser PUTs the
file straight to MinIO using the returned URL; this service never touches the
file bytes.
"""
import uuid

from fastapi import HTTPException, status
from src.config.settings import settings
from src.utils.s3_client import generate_presigned_put_url

# Allowed upload content types mapped to the stored object extension.
ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
}


class UploadService:
    """Service class for generating pre-signed upload URLs."""

    @staticmethod
    def presigned_question_image_upload(content_type: str) -> dict:
        """
        Generate a pre-signed PUT URL for a question image.

        The object key is server-generated (questions/{uuid}.{ext}) — the
        client filename is never trusted, and the extension is derived from
        the validated content type.
        """
        ext = ALLOWED_IMAGE_TYPES.get(content_type)
        if ext is None:
            allowed = ", ".join(sorted(ALLOWED_IMAGE_TYPES))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported content_type '{content_type}'. Allowed: {allowed}",
            )

        key = f"questions/{uuid.uuid4().hex}.{ext}"
        url = generate_presigned_put_url(key=key, content_type=content_type)
        return {
            "upload_url": url,
            "object_key": key,
            "expires_in": settings.S3_PRESIGN_EXPIRY_SECONDS,
        }
