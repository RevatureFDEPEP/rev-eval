"""
JWT authentication middleware for the API Gateway.

Verifies HS256 tokens issued by user-service, extracts the user context,
and injects it as X-User-* headers for downstream services.
"""
import os
from typing import Dict, Optional

import jwt
from fastapi import Header, HTTPException, status

_JWT_SECRET_ENV = "JWT_SECRET"
_JWT_ALGORITHM_ENV = "JWT_ALGORITHM"
_JWT_ISSUER_ENV = "JWT_ISSUER"
_JWT_AUDIENCE_ENV = "JWT_AUDIENCE"
_JWT_MIN_SECRET_LENGTH_ENV = "JWT_MIN_SECRET_LENGTH"
_ALLOW_INSECURE_ENV = "ALLOW_INSECURE_DEV_SECRETS"
_DEFAULT_ALGORITHM = "HS256"
_DEFAULT_ISSUER = "rev-eval-user-service"
_DEFAULT_AUDIENCE = "rev-eval-clients"

# Valid role claim values. A token whose role is missing or outside this set is
# rejected for authenticated routes.
KNOWN_ROLES = {"TRAINER", "PARTICIPANT", "ADMIN"}

_PLACEHOLDER_SECRETS = {
    "",
    "change-me-in-production",
    "changeme",
    "change-me",
    "secret",
    "your-secret-key",
    "dev",
    "development",
    "test",
}


def _get_secret() -> str:
    secret = os.getenv(_JWT_SECRET_ENV)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{_JWT_SECRET_ENV} not configured",
        )
    return secret


def validate_jwt_secret() -> None:
    """Raise RuntimeError at startup when the configured JWT secret is unsafe.

    Unsafe = missing, empty, a known placeholder, or shorter than the minimum
    length. ALLOW_INSECURE_DEV_SECRETS=true bypasses this for local dev only.
    """
    secret = (os.getenv(_JWT_SECRET_ENV) or "").strip()
    min_length = int(os.getenv(_JWT_MIN_SECRET_LENGTH_ENV, "32"))
    allow_insecure = os.getenv(_ALLOW_INSECURE_ENV, "").lower() in ("1", "true", "yes")
    unsafe = (
        not secret
        or secret.lower() in _PLACEHOLDER_SECRETS
        or len(secret) < min_length
    )
    if unsafe and not allow_insecure:
        raise RuntimeError(
            "JWT_SECRET is missing, a known default/placeholder, or shorter than "
            f"{min_length} characters. Set a strong JWT_SECRET, or set "
            "ALLOW_INSECURE_DEV_SECRETS=true for local development only."
        )


async def verify_jwt_token(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Verify a Bearer JWT and return a user-context dict (user_id, email, role).

    Enforces signature, algorithm, expiry, not-before, issued-at, issuer,
    audience, a subject claim, and a known role claim.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer {token}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    algorithm = os.getenv(_JWT_ALGORITHM_ENV, _DEFAULT_ALGORITHM)
    issuer = os.getenv(_JWT_ISSUER_ENV, _DEFAULT_ISSUER)
    audience = os.getenv(_JWT_AUDIENCE_ENV, _DEFAULT_AUDIENCE)

    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "nbf", "sub", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    role = (payload.get("role") or "").upper()
    if role not in KNOWN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing or has an unknown role claim",
        )

    return {
        "user_id": str(user_id),
        "email": payload.get("email", ""),
        "role": role,
    }


def strip_client_identity_headers(headers: dict) -> dict:
    """Drop any client-supplied identity / internal-trust headers.

    Downstream services trust X-User-* as gateway-verified identity and
    X-Internal-Key as proof of a trusted in-network caller. A client must never
    be able to set either directly, so we remove every casing of them before the
    gateway injects the values derived from the verified JWT. The internal key
    is only ever presented on direct service-to-service calls that never
    traverse the gateway.
    """
    return {
        k: v
        for k, v in headers.items()
        if not k.lower().startswith("x-user-") and k.lower() != "x-internal-key"
    }


def add_user_context_headers(headers: dict, user_context: Dict[str, str]) -> dict:
    """Inject gateway-verified X-User-* headers for downstream services.

    Strips any inbound X-User-* first so a spoofed header can never survive.
    """
    headers_copy = strip_client_identity_headers(headers)
    headers_copy["X-User-Id"] = str(user_context.get("user_id") or "")
    headers_copy["X-User-Email"] = str(user_context.get("email") or "")
    headers_copy["X-User-Role"] = str(user_context.get("role") or "")
    return headers_copy
