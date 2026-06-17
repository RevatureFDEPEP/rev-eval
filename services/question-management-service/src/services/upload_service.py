"""
Presigned-upload service for question images.

Core logic is deliberately kept free of FastAPI and Mongo/Beanie so it can be
unit-tested by mocking only the S3 helper. The HTTP route is a thin wrapper
around `create_presigned_upload`.
"""

from __future__ import annotations

import os
from uuid import uuid4

from src.config.settings import settings
from src.utils import s3_client

# Allowlist of MIME types accepted for question images. Anything else is a
# client error — we never sign a URL for an arbitrary content type.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"image/png", "image/jpeg"})

# Object-key prefix so all question images live under a predictable namespace.
KEY_PREFIX = "questions"


class InvalidContentTypeError(ValueError):
    """Raised when a requested content_type is not in the allowlist."""

    def __init__(self, content_type: str) -> None:
        self.content_type = content_type
        super().__init__(
            f"content_type {content_type!r} not allowed; "
            f"allowed types: {sorted(ALLOWED_CONTENT_TYPES)}"
        )


class InvalidFilenameError(ValueError):
    """Raised when a filename is empty or unusable after sanitization."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__("filename must be a non-empty value")


def _sanitize_filename(filename: str) -> str:
    """
    Reduce a client-supplied filename to a safe basename.

    Strips any directory components (defends against path traversal like
    ``../../etc/passwd``) and surrounding whitespace. The unique UUID segment
    in the key is what guarantees no collisions, so the basename is purely
    cosmetic/extension-preserving.
    """
    base = os.path.basename((filename or "").strip()).strip()
    if not base or base in {".", ".."}:
        raise InvalidFilenameError(filename)
    return base


def build_object_key(filename: str) -> str:
    """
    Build a collision-free object key for a question image.

    Shape: ``questions/<uuid4-hex>/<sanitized-filename>``. The uuid segment
    makes every key unique even for identical filenames.
    """
    safe_name = _sanitize_filename(filename)
    return f"{KEY_PREFIX}/{uuid4().hex}/{safe_name}"


def create_presigned_upload(
    filename: str,
    content_type: str,
    *,
    ensure_bucket: bool = True,
) -> dict[str, object]:
    """
    Validate inputs, build a unique key, and return a presigned POST policy.

    A presigned POST (not PUT) is used so the ``content-length-range`` condition
    enforces the 5 MiB ceiling server-side — a PUT URL only binds Content-Type.

    Does NOT touch Mongo. Returns a dict matching the response contract:
    ``{"url": str, "fields": dict, "key": str, "expires_in": int,
    "max_bytes": int}``. The client POSTs multipart form-data (``fields`` plus
    the file) to ``url``.

    Raises:
        InvalidContentTypeError: content_type is not in the allowlist.
        InvalidFilenameError: filename is empty/unusable.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidContentTypeError(content_type)

    key = build_object_key(filename)

    # Lazily make sure the target bucket exists. Disable in unit tests to keep
    # the function pure (no network); the route enables it.
    if ensure_bucket:
        s3_client.ensure_bucket()

    expires_in = settings.S3_PRESIGN_EXPIRY_SECONDS
    max_bytes = s3_client.MAX_UPLOAD_BYTES
    presigned = s3_client.generate_presigned_post(
        key=key,
        content_type=content_type,
        expires_in=expires_in,
        max_bytes=max_bytes,
    )

    return {
        "url": presigned["url"],
        "fields": presigned["fields"],
        "key": key,
        "expires_in": expires_in,
        "max_bytes": max_bytes,
    }
