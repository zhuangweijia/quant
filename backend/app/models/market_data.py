import uuid
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import String, Numeric, BigInteger, Index, UniqueConstraint, Date, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class MarketData(TimestampMixin, Base):
    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "market",
            "timeframe",
            "timestamp",
            name="uq_market_data_symbol_tf_ts",
        ),
        Index(
            "ix_market_data_lookup",
            "symbol",
            "market",
            "timeframe",
            "timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BacktestResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_results"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )
    total_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    annual_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    sortino_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    max_drawdown: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    calmar_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    win_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    profit_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    trade_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_holding_period: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    equity_curve: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    drawdown_curve: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    trades: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    monthly_returns: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="running", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )

    strategy = relationship("Strategy", back_populates="backtest_results")
    user = relationship("User")
