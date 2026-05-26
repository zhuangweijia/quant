import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, String, JSON, Uuid as UuidType
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_is_sqlite = _settings.DATABASE_URL.startswith("sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


JsonType = JSON
