from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Strategy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategies"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy", lazy="selectin")
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy", lazy="selectin"
    )
