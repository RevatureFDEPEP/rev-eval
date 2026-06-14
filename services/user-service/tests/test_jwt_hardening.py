"""Phase 4 regression: JWT claim enforcement and unsafe-secret fail-fast."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from src.config.settings import settings
from src.services.auth_service import KNOWN_ROLES, AuthService, validate_jwt_secret


def _encode(payload):
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _base_claims(**overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1",
        "email": "a@example.com",
        "role": "TRAINER",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    claims.update(overrides)
    return claims


def test_issued_token_round_trips_with_all_claims():
    token = AuthService.create_access_token({"sub": "1", "email": "a@example.com", "role": "TRAINER"})
    payload = AuthService.decode_access_token(token)
    for claim in ("sub", "iat", "nbf", "exp", "iss", "aud"):
        assert claim in payload
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE


def test_decode_rejects_wrong_issuer():
    with pytest.raises(jwt.InvalidIssuerError):
        AuthService.decode_access_token(_encode(_base_claims(iss="evil")))


def test_decode_rejects_wrong_audience():
    with pytest.raises(jwt.InvalidAudienceError):
        AuthService.decode_access_token(_encode(_base_claims(aud="evil")))


def test_decode_rejects_expired():
    now = datetime.now(timezone.utc)
    claims = _base_claims(exp=now - timedelta(minutes=1), iat=now - timedelta(minutes=5),
                          nbf=now - timedelta(minutes=5))
    with pytest.raises(jwt.ExpiredSignatureError):
        AuthService.decode_access_token(_encode(claims))


def test_decode_rejects_future_nbf():
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    with pytest.raises(jwt.ImmatureSignatureError):
        AuthService.decode_access_token(_encode(_base_claims(nbf=future, iat=future)))


def test_decode_rejects_missing_required_claim():
    with pytest.raises(jwt.MissingRequiredClaimError):
        AuthService.decode_access_token(_encode({"email": "a@example.com", "role": "TRAINER"}))


def test_known_roles_match_enum():
    assert KNOWN_ROLES == {"TRAINER", "PARTICIPANT", "ADMIN"}


# --- secret validation --------------------------------------------------------

def test_validate_jwt_secret_rejects_default():
    with pytest.raises(RuntimeError):
        validate_jwt_secret("change-me-in-production", min_length=32, allow_insecure=False)


def test_validate_jwt_secret_rejects_short():
    with pytest.raises(RuntimeError):
        validate_jwt_secret("short", min_length=32, allow_insecure=False)


def test_validate_jwt_secret_rejects_empty():
    with pytest.raises(RuntimeError):
        validate_jwt_secret("", min_length=32, allow_insecure=False)


def test_validate_jwt_secret_escape_hatch_allows_weak():
    validate_jwt_secret("change-me-in-production", min_length=32, allow_insecure=True)


def test_validate_jwt_secret_accepts_strong():
    validate_jwt_secret("a-sufficiently-long-random-production-secret-123", min_length=32,
                        allow_insecure=False)
