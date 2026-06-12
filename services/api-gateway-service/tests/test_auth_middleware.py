import os

import jwt
import pytest
import pytest_asyncio
from src.middleware.auth import add_user_context_headers, verify_jwt_token

_SECRET = os.environ.get("JWT_SECRET", "test-secret-for-gateway-tests")


@pytest.mark.parametrize("role", ["TRAINER", "PARTICIPANT"])
def test_add_user_context_headers_injects_all_x_user_fields(role):
    original = {"Content-Type": "application/json"}
    ctx = {"user_id": "7", "email": "dev@corp.com", "role": role}
    result = add_user_context_headers(original, ctx)
    assert result["X-User-Id"] == "7"
    assert result["X-User-Email"] == "dev@corp.com"
    assert result["X-User-Role"] == role
    assert result.get("Content-Type") == "application/json"


@pytest.mark.asyncio
async def test_verify_jwt_token_returns_user_context_for_valid_token():
    token = jwt.encode(
        {"sub": "42", "email": "user@example.com", "role": "TRAINER"},
        _SECRET,
        algorithm="HS256",
    )
    ctx = await verify_jwt_token(f"Bearer {token}")
    assert ctx["user_id"] == "42"
    assert ctx["email"] == "user@example.com"
    assert ctx["role"] == "TRAINER"
