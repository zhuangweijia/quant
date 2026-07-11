from datetime import date
from decimal import Decimal

from sqlalchemy import String, Numeric, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StockFactor(TimestampMixin, Base):
    """Wide-table design: one row per symbol+date, columns for each factor."""

    __tablename__ = "stock_factors"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_stock_factors_symbol_date"),
        Index("ix_stock_factors_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Momentum factors
    return_5d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    return_10d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    return_20d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    return_60d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    excess_return_20d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    momentum_12_1: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    # Valuation factors
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    pb: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    ps_ttm: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    pe_industry_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pb_industry_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    # Quality factors
    roe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    debt_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    cashflow_to_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Growth factors
    revenue_yoy: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    profit_yoy: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    revenue_qoq: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Volume-price factors
    turnover_5d_avg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    volatility_20d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    vol_price_corr_20d: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    volume_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Technical factors
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd_hist: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    boll_position: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    ma_alignment: Mapped[Decimal | None] = mapped_column(Numeric(2, 0), nullable=True)

    # Fund flow factors
    northbound_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    northbound_holding_change: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
