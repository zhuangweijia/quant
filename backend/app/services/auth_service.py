from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.core.passwords import validate_bcrypt_password_size


class AuthService:
    _private_key: str | None = None
    _public_key: str | None = None

    @classmethod
    def _get_private_key(cls) -> str:
        if cls._private_key is None:
            settings = get_settings()
            cls._private_key = Path(settings.JWT_PRIVATE_KEY_PATH).read_text()
        return cls._private_key

    @classmethod
    def _get_public_key(cls) -> str:
        if cls._public_key is None:
            settings = get_settings()
            cls._public_key = Path(settings.JWT_PUBLIC_KEY_PATH).read_text()
        return cls._public_key

    @classmethod
    def hash_password(cls, password: str) -> str:
        validate_bcrypt_password_size(password)
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    @classmethod
    def verify_password(cls, plain: str, hashed: str) -> bool:
        try:
            validate_bcrypt_password_size(plain)
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False

    @classmethod
    def create_access_token(cls, user_id: str, role: str) -> str:
        settings = get_settings()
        expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "role": role,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, cls._get_private_key(), algorithm=settings.JWT_ALGORITHM)

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        settings = get_settings()
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {"sub": user_id, "exp": expire, "type": "refresh"}
        return jwt.encode(payload, cls._get_private_key(), algorithm=settings.JWT_ALGORITHM)

    @classmethod
    def decode_token(cls, token: str) -> dict | None:
        settings = get_settings()
        try:
            payload = jwt.decode(token, cls._get_public_key(), algorithms=[settings.JWT_ALGORITHM])
            return payload
        except (JWTError, Exception):
            return None
