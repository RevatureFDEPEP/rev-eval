"""
HTTP integration tests for the user management routes.
Uses `client` and `auth_headers` fixtures from conftest.py.

Notes:
  - auth_headers fixture registers "test@example.com" — that user gets id=1
    in the fresh SQLite DB created per test function.
  - Routes /users/by-email/{email}, /users/{user_id}, /users/, and /users/invite
    do NOT require authentication.
  - Route /users/me DOES require authentication.
"""

REGISTER_URL = "/v1/api/auth/register"
USERS_BASE = "/v1/api/users"


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------

def test_get_user_by_id_found(client, auth_headers):
    # auth_headers fixture already registered user id=1
    resp = client.get(f"{USERS_BASE}/1", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert "email" in body


def test_get_user_by_id_not_found(client):
    # No auth needed for this route
    resp = client.get(f"{USERS_BASE}/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/by-email/{email}
# ---------------------------------------------------------------------------

def test_get_user_by_email_found(client, auth_headers):
    resp = client.get(f"{USERS_BASE}/by-email/test@example.com", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_get_user_by_email_not_found(client):
    resp = client.get(f"{USERS_BASE}/by-email/nobody@x.com")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/
# ---------------------------------------------------------------------------

def test_list_users(client):
    # Seed a couple of users first
    client.post(
        REGISTER_URL,
        json={
            "email": "list_user1@example.com",
            "password": "password123",
            "role": "PARTICIPANT",
        },
    )
    client.post(
        REGISTER_URL,
        json={
            "email": "list_user2@example.com",
            "password": "password123",
            "role": "TRAINER",
        },
    )
    resp = client.get(f"{USERS_BASE}/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2


def test_list_users_filter_by_role(client):
    client.post(
        REGISTER_URL,
        json={
            "email": "participant_only@example.com",
            "password": "password123",
            "role": "PARTICIPANT",
        },
    )
    resp = client.get(f"{USERS_BASE}/", params={"role": "PARTICIPANT"})
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    for user in users:
        assert user["role"] == "PARTICIPANT"


# ---------------------------------------------------------------------------
# POST /users/invite
# ---------------------------------------------------------------------------

def test_invite_user_new(client):
    resp = client.post(
        f"{USERS_BASE}/invite",
        json={
            "email": "invited_new@example.com",
            "first_name": "Invited",
            "last_name": "User",
            "role": "PARTICIPANT",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "invited_new@example.com"
    assert "id" in body


def test_invite_user_duplicate(client, auth_headers):
    # auth_headers already created test@example.com — invite the same address
    resp = client.post(
        f"{USERS_BASE}/invite",
        json={"email": "test@example.com", "role": "PARTICIPANT"},
    )
    # Route always returns 201; service returns "User already exists"
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert body["invite_sent"] is False


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}
# ---------------------------------------------------------------------------

def test_update_user(client, auth_headers):
    resp = client.patch(
        f"{USERS_BASE}/1",
        json={"first_name": "Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


def test_update_user_not_found(client):
    resp = client.patch(
        f"{USERS_BASE}/9999",
        json={"first_name": "Ghost"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

def test_get_users_me_authenticated(client, auth_headers):
    resp = client.get(f"{USERS_BASE}/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "email" in body
    assert body["email"] == "test@example.com"
