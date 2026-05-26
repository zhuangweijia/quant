import uuid

from sqlalchemy import String, Text, ForeignKey, Boolean, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
