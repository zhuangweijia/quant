import uuid
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Numeric, Index, Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_strategy_created", "strategy_id", "created_at"),
        Index("ix_orders_symbol", "symbol"),
    )

    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    filled_qty: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )
    filled_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    commission: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    strategy = relationship("Strategy", back_populates="orders")
    user = relationship("User")
