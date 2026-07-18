import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.settings import PasswordChangeRequest
from app.services.auth_service import AuthService

OVERSIZED_MULTIBYTE_PASSWORD = "a1" + "测" * 24


def test_password_change_rejects_more_than_72_utf8_bytes():
    with pytest.raises(ValidationError, match="72"):
        PasswordChangeRequest(
            old_password="current123",
            new_password=OVERSIZED_MULTIBYTE_PASSWORD,
            confirm_password=OVERSIZED_MULTIBYTE_PASSWORD,
        )


def test_registration_and_login_reject_more_than_72_utf8_bytes():
    with pytest.raises(ValidationError, match="72"):
        RegisterRequest(
            username="alice",
            password=OVERSIZED_MULTIBYTE_PASSWORD,
            confirm_password=OVERSIZED_MULTIBYTE_PASSWORD,
        )
    with pytest.raises(ValidationError, match="72"):
        LoginRequest(username="alice", password=OVERSIZED_MULTIBYTE_PASSWORD)


def test_auth_service_rejects_oversized_hash_input_and_safely_fails_verification():
    with pytest.raises(ValueError, match="72"):
        AuthService.hash_password(OVERSIZED_MULTIBYTE_PASSWORD)

    stored_hash = AuthService.hash_password("password123")
    assert AuthService.verify_password(OVERSIZED_MULTIBYTE_PASSWORD, stored_hash) is False
