from src.services.auth_service import AuthService


def test_verify_password_returns_true_for_correct_password():
    hashed = AuthService.hash_password("secret123")
    assert AuthService.verify_password("secret123", hashed) is True


def test_verify_password_returns_false_for_wrong_password():
    hashed = AuthService.hash_password("secret123")
    assert AuthService.verify_password("wrong", hashed) is False


def test_verify_password_returns_false_for_empty_hash():
    assert AuthService.verify_password("secret123", "") is False
