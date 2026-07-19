import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JsonType, TimestampMixin, UUIDMixin


class ExecutionRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execution_records"
    __table_args__ = (UniqueConstraint("advice_item_id", name="uq_execution_item"),)

    advice_item_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("advice_items.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    disposition: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    within_price_band: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ExecutionMutation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execution_mutations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_execution_mutation_key"),)

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("execution_records.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    after_state: Mapped[dict] = mapped_column(JsonType, nullable=False)
    portfolio_event_ids: Mapped[list] = mapped_column(JsonType, nullable=False)
