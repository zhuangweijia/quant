import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JsonType, TimestampMixin, UUIDMixin


class DailyAdvice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "daily_advices"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "signal_date", "version", name="uq_advice_user_signal_version"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("investment_profiles.id")
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolio_snapshots.id")
    )
    signal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="ready", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_exposure: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    target_exposure: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    estimated_cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("daily_advices.id"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)


class AdviceItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "advice_items"
    __table_args__ = (UniqueConstraint("advice_id", "symbol", name="uq_advice_item_symbol"),)

    advice_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("daily_advices.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_weight: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price_tolerance: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    positive_factors: Mapped[list] = mapped_column(JsonType, nullable=False)
    risks: Mapped[list] = mapped_column(JsonType, nullable=False)
    invalidation_conditions: Mapped[list] = mapped_column(JsonType, nullable=False)
    constraint_notes: Mapped[list] = mapped_column(JsonType, nullable=False)
