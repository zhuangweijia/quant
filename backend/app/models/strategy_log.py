from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class StrategyLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategy_logs"
    __table_args__ = (
        Index("ix_strategy_logs_strategy_created", "strategy_id", "created_at"),
    )

    strategy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(8), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
