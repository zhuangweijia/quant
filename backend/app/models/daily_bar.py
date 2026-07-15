from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyBar(TimestampMixin, Base):
    __tablename__ = "daily_bars"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_daily_bars_symbol_date"),
        Index("ix_daily_bars_symbol_date", "symbol", "trade_date"),
        Index("ix_daily_bars_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
