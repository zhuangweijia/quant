import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Setting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "key", name="uq_settings_user_cat_key"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
