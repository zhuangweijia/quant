import uuid
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Numeric, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Account(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    mode: Mapped[str] = mapped_column(String(8), default="paper", nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("1000000"), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("1000000"), nullable=False
    )

    user = relationship("User")
