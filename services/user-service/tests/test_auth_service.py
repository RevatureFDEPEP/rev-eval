import pytest
from src.services.auth_service import AuthService
from src.models.user import UserRole


class TestPasswordHashing:
    @pytest.mark.parametrize("plaintext", [
        "password123",
        "s3cur3!P@ssw0rd",
        "short8!",
    ])
    def test_hash_differs_from_plaintext(self, plaintext):
        hashed = AuthService.hash_password(plaintext)
        assert hashed != plaintext
        assert len(hashed) > 0

    @pytest.mark.parametrize("plaintext", [
        "password123",
        "s3cur3!P@ssw0rd",
    ])
    def test_verify_correct_password(self, plaintext):
        hashed = AuthService.hash_password(plaintext)
        assert AuthService.verify_password(plaintext, hashed) is True

    @pytest.mark.parametrize("plaintext,wrong", [
        ("password123", "wrongpassword"),
        ("secret", "SECRET"),
        ("abc123", "abc124"),
    ])
    def test_verify_wrong_password_returns_false(self, plaintext, wrong):
        hashed = AuthService.hash_password(plaintext)
        assert AuthService.verify_password(wrong, hashed) is False

    def test_verify_empty_hash_returns_false(self):
        assert AuthService.verify_password("anything", "") is False

    def test_verify_none_hash_returns_false(self):
        assert AuthService.verify_password("anything", None) is False

    def test_same_password_produces_different_hashes(self):
        h1 = AuthService.hash_password("password")
        h2 = AuthService.hash_password("password")
        assert h1 != h2  # bcrypt uses random salt


class TestJWTTokens:
    def test_create_and_decode_roundtrip(self):
        data = {"sub": "42", "email": "user@example.com", "role": "PARTICIPANT"}
        token = AuthService.create_access_token(data)
        decoded = AuthService.decode_access_token(token)
        assert decoded["sub"] == "42"
        assert decoded["email"] == "user@example.com"

    def test_token_contains_expiry(self):
        token = AuthService.create_access_token({"sub": "1"})
        decoded = AuthService.decode_access_token(token)
        assert "exp" in decoded

    @pytest.mark.parametrize("payload", [
        {"sub": "1", "email": "a@b.com"},
        {"sub": "999", "role": "TRAINER"},
    ])
    def test_custom_payloads_preserved(self, payload):
        token = AuthService.create_access_token(payload)
        decoded = AuthService.decode_access_token(token)
        for key, val in payload.items():
            assert decoded[key] == val

    def test_invalid_token_raises(self):
        import jwt
        with pytest.raises(jwt.PyJWTError):
            AuthService.decode_access_token("not.a.valid.token")

    def test_tampered_token_raises(self):
        import jwt
        token = AuthService.create_access_token({"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.PyJWTError):
            AuthService.decode_access_token(tampered)


class TestUserCRUD:
    def test_create_user_returns_with_id(self, db):
        user = AuthService.create_user(db, "new@example.com", "password123")
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.is_active is True

    def test_create_user_stores_hashed_password(self, db):
        user = AuthService.create_user(db, "hash@example.com", "password123")
        assert user.password_hash != "password123"
        assert user.password_hash is not None

    def test_create_user_splits_full_name(self, db):
        user = AuthService.create_user(db, "name@example.com", "password123", full_name="Jane Doe")
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"

    def test_create_user_single_name(self, db):
        user = AuthService.create_user(db, "single@example.com", "password123", full_name="Cher")
        assert user.first_name == "Cher"
        assert user.last_name is None

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_create_user_with_explicit_role(self, db, role):
        user = AuthService.create_user(db, f"{role.lower()}@example.com", "password123", role=role)
        assert user.role == role

    def test_get_user_by_email_found(self, db):
        AuthService.create_user(db, "find@example.com", "password123")
        found = AuthService.get_user_by_email(db, "find@example.com")
        assert found is not None
        assert found.email == "find@example.com"

    def test_get_user_by_email_not_found(self, db):
        assert AuthService.get_user_by_email(db, "ghost@example.com") is None

    def test_get_user_by_id_found(self, db):
        user = AuthService.create_user(db, "byid@example.com", "password123")
        found = AuthService.get_user_by_id(db, user.id)
        assert found is not None
        assert found.id == user.id

    def test_get_user_by_id_not_found(self, db):
        assert AuthService.get_user_by_id(db, 99999) is None


class TestAuthentication:
    def test_authenticate_valid_credentials(self, db):
        AuthService.create_user(db, "auth@example.com", "password123")
        result = AuthService.authenticate_user(db, "auth@example.com", "password123")
        assert result is not None
        assert result.email == "auth@example.com"

    def test_authenticate_wrong_password_returns_none(self, db):
        AuthService.create_user(db, "wrongpw@example.com", "password123")
        result = AuthService.authenticate_user(db, "wrongpw@example.com", "wrongpassword")
        assert result is None

    def test_authenticate_nonexistent_email_returns_none(self, db):
        assert AuthService.authenticate_user(db, "nobody@example.com", "password123") is None

    def test_authenticate_inactive_user_returns_none(self, db):
        user = AuthService.create_user(db, "inactive@example.com", "password123")
        user.is_active = False
        db.commit()
        assert AuthService.authenticate_user(db, "inactive@example.com", "password123") is None

    @pytest.mark.parametrize("password", ["password123", "s3cur3!", "longpassword!"])
    def test_authenticate_updates_last_login(self, db, password):
        AuthService.create_user(db, f"{password[:4]}@example.com", password)
        result = AuthService.authenticate_user(db, f"{password[:4]}@example.com", password)
        assert result is not None
        assert result.last_login is not None
