"""
JWT Authentication Middleware for API Gateway

Verifies WorkOS JWT tokens and extracts user context.
"""
import os
from typing import Optional, Dict
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import httpx
import json
from datetime import datetime

# WorkOS API URLs
WORKOS_JWKS_URL = "https://api.workos.com/sso/jwks/{client_id}"

# Cache for JWKS (in production, use Redis or similar)
_jwks_cache: Optional[Dict] = None
_jwks_cache_time: Optional[datetime] = None
CACHE_DURATION_SECONDS = 3600  # 1 hour


async def get_workos_jwks() -> Dict:
    """
    Fetch WorkOS JWKS (JSON Web Key Set) for JWT verification.
    Caches the result for 1 hour to avoid excessive API calls.
    """
    global _jwks_cache, _jwks_cache_time

    # Check if cache is still valid
    if _jwks_cache and _jwks_cache_time:
        elapsed = (datetime.now() - _jwks_cache_time).total_seconds()
        if elapsed < CACHE_DURATION_SECONDS:
            return _jwks_cache

    # Fetch new JWKS
    client_id = os.getenv("WORKOS_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WORKOS_CLIENT_ID not configured"
        )

    jwks_url = WORKOS_JWKS_URL.format(client_id=client_id)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = datetime.now()
            return _jwks_cache
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS from WorkOS: {str(e)}"
        )


async def verify_workos_token(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """
    Verify WorkOS JWT token and extract user context.

    Args:
        authorization: Authorization header value (Bearer {token})

    Returns:
        Dict containing user context:
        - user_id: User identifier
        - email: User email
        - role: User role (trainer, associate, admin)
        - organization_id: Organization identifier

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer {token}" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer {token}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        # Decode token header to get key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'kid' in header"
            )

        # Get JWKS and find matching key
        jwks = await get_workos_jwks()
        keys = jwks.get("keys", [])

        # Find the key matching the kid
        public_key = None
        for key in keys:
            if key.get("kid") == kid:
                public_key = key
                break

        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Public key not found for kid: {kid}"
            )

        # Verify and decode JWT
        client_id = os.getenv("WORKOS_CLIENT_ID")
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=client_id,
            options={"verify_aud": True, "verify_exp": True}
        )

        # Extract user context from JWT payload
        # Note: Email and name are NOT in the JWT - user-service will fetch from WorkOS if needed
        user_id = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' (user_id) claim"
            )

        user_context = {
            "user_id": user_id,
            "role": map_workos_role_to_app_role(payload.get("role", "")),
            "organization_id": payload.get("org_id") or payload.get("organization_id", ""),
        }

        print(f"✅ User authenticated: {user_id} - Role: {user_context['role']}")

        return user_context

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )


def map_workos_role_to_app_role(workos_role: str) -> str:
    """
    Map WorkOS organization role to application role.

    Args:
        workos_role: Role from WorkOS (e.g., 'org-trainer', 'org-participant')

    Returns:
        Application role: 'TRAINER', 'PARTICIPANT', or 'ADMIN' (uppercase to match database enum)
    """
    role_mapping = {
        "org-trainer": "TRAINER",
        "trainer": "TRAINER",
        "org-admin": "ADMIN",
        "admin": "ADMIN",
        "org-participant": "PARTICIPANT",
        "participant": "PARTICIPANT",
        "associate": "PARTICIPANT",
        "member": "PARTICIPANT",
    }

    return role_mapping.get(workos_role.lower(), "PARTICIPANT")


def add_user_context_headers(headers: dict, user_context: Dict[str, str]) -> dict:
    """
    Add user context to request headers for downstream services.

    Args:
        headers: Existing request headers
        user_context: User context from JWT verification

    Returns:
        Updated headers dict
    """
    headers_copy = headers.copy()

    # Add minimal user context from JWT (user-service will fetch full details from WorkOS if needed)
    headers_copy["X-User-Id"] = str(user_context.get("user_id") or "")
    headers_copy["X-User-Role"] = str(user_context.get("role") or "")
    headers_copy["X-Organization-Id"] = str(user_context.get("organization_id") or "")

    return headers_copy
