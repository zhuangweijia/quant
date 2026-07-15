import os
import sys

import structlog
from cryptography.fernet import Fernet

from app.config import get_settings

logger = structlog.get_logger()


async def validate_config() -> None:
    if os.environ.get("SKIP_CONFIG_VALIDATION", "").lower() == "true":
        logger.warning("config.validation_skipped")
        return

    settings = get_settings()
    errors: list[str] = []

    _validate_encryption_key(settings, errors)
    _validate_jwt_keys(settings, errors)
    await _validate_database(errors)

    if errors:
        for e in errors:
            logger.error("config.validation_failed", error=e)
        sys.exit(1)

    logger.info("config.validation_passed")


def _validate_encryption_key(settings, errors: list[str]) -> None:
    key = settings.ENCRYPTION_KEY
    if not key:
        errors.append("ENCRYPTION_KEY is not configured. Set it in backend/.env")
        return
    try:
        Fernet(key.encode() if len(key) == 44 else key.encode())
    except Exception as e:
        errors.append(f"ENCRYPTION_KEY is invalid: {e}")


def _validate_jwt_keys(settings, errors: list[str]) -> None:
    for attr, label in [
        ("JWT_PRIVATE_KEY_PATH", "JWT private key"),
        ("JWT_PUBLIC_KEY_PATH", "JWT public key"),
    ]:
        path = getattr(settings, attr)
        if not os.path.isfile(path):
            errors.append(f"{label} file not found: {path}")


async def _validate_database(errors: list[str]) -> None:
    try:
        from sqlalchemy import text

        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"Database connection failed: {e}")
