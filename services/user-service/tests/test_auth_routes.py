"""
HTTP integration tests for the authentication routes.
Uses the `client` and `auth_headers` fixtures from conftest.py.
"""

REGISTER_URL = "/v1/api/auth/register"
LOGIN_URL = "/v1/api/auth/login"
ME_URL = "/v1/api/auth/me"

_VALID_REGISTER = {
    "email": "route_test@example.com",
    "password": "validpass123",
    "full_name": "Route Test",
    "role": "PARTICIPANT",
}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def test_register_success(client):
    resp = client.post(REGISTER_URL, json=_VALID_REGISTER)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == _VALID_REGISTER["email"]


def test_register_duplicate_email(client):
    client.post(REGISTER_URL, json=_VALID_REGISTER)
    resp = client.post(REGISTER_URL, json=_VALID_REGISTER)
    assert resp.status_code == 400


def test_register_short_password(client):
    payload = {**_VALID_REGISTER, "password": "abc"}
    resp = client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success(client):
    client.post(REGISTER_URL, json=_VALID_REGISTER)
    resp = client.post(
        LOGIN_URL,
        json={"email": _VALID_REGISTER["email"], "password": _VALID_REGISTER["password"]},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post(REGISTER_URL, json=_VALID_REGISTER)
    resp = client.post(
        LOGIN_URL,
        json={"email": _VALID_REGISTER["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        LOGIN_URL,
        json={"email": "nobody@example.com", "password": "somepassword"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

def test_get_me_authenticated(client, auth_headers):
    resp = client.get(ME_URL, headers=auth_headers)
    assert resp.status_code == 200
    assert "email" in resp.json()


def test_get_me_no_token(client):
    resp = client.get(ME_URL)
    assert resp.status_code in (401, 403)
