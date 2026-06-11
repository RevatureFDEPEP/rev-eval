"""
Business logic for direct-to-MinIO question image uploads.

Stateless presigning only — no repository layer. The browser POSTs the file
bytes straight to MinIO using the returned policy; this service never touches
the bytes. A pre-signed POST (not PUT) is used so the upload size ceiling is
enforced server-side via the content-length-range condition.
"""
import uuid

from fastapi import HTTPException, status

from src.config.settings import settings
from src.utils.s3_client import generate_presigned_post

# Allowed upload content types mapped to the stored object extension.
ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
}


class UploadService:
    """Service for generating pre-signed upload policies for question images."""

    @staticmethod
    def presigned_question_image_upload(content_type: str) -> dict:
        """Generate a pre-signed POST policy for a question image.

        The object key is server-generated (``questions/{uuid}.{ext}``) — the
        client filename is never trusted, and the extension is derived from the
        validated content type. The 5 MB ceiling is baked into the policy.

        Raises:
            HTTPException: 400 if the content type is not an allowed image type.
        """
        ext = ALLOWED_IMAGE_TYPES.get(content_type)
        if ext is None:
            allowed = ", ".join(sorted(ALLOWED_IMAGE_TYPES))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported content_type '{content_type}'. Allowed: {allowed}",
            )

        key = f"questions/{uuid.uuid4().hex}.{ext}"
        policy = generate_presigned_post(
            key=key,
            content_type=content_type,
            max_bytes=settings.S3_MAX_UPLOAD_BYTES,
        )
        return {
            "url": policy["url"],
            "fields": policy["fields"],
            "object_key": key,
            "max_bytes": settings.S3_MAX_UPLOAD_BYTES,
            "expires_in": settings.S3_PRESIGN_EXPIRY_SECONDS,
        }
