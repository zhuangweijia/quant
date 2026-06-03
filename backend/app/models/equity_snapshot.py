import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Numeric, UniqueConstraint, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class EquitySnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "equity_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "timestamp", name="uq_equity_snapshot_user_timestamp"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    position_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"), nullable=False)
