import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Date, ForeignKey, Numeric, UniqueConstraint, DateTime, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class EquitySnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "equity_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_equity_snapshot_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    position_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"), nullable=False)
