from datetime import date
from decimal import Decimal

from sqlalchemy import String, Numeric, Date, Integer, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Prediction(TimestampMixin, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", "model_version", name="uq_predictions_sym_date_ver"),
        Index("ix_predictions_date", "trade_date"),
        Index("ix_predictions_date_rank", "trade_date", "rank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    explanation: Mapped[dict | None] = mapped_column(postgresql.JSONB, nullable=True)
    rank_change: Mapped[int | None] = mapped_column(Integer, nullable=True)
