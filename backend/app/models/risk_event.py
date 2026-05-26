import uuid

from sqlalchemy import String, Text, ForeignKey, Index, JSON, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class RiskEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_events"
    __table_args__ = (
        Index("ix_risk_events_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("risk_rules.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
