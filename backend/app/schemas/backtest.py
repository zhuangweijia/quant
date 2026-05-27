from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    strategy_id: UUID
    symbol: str = Field(..., min_length=1, max_length=32)
    market: str = Field(..., pattern=r"^(a_stock|us_stock|crypto)$")
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|30m|1h|4h|1d|1w)$")
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0)
    commission_rate: Decimal | None = None
    slippage: Decimal = Field(default=Decimal("0.001"))
    params: dict | None = None


class BacktestResultListItem(BaseModel):
    id: UUID
    strategy_id: UUID
    symbol: str
    start_date: date
    end_date: date
    total_return: Decimal | None
    sharpe_ratio: Decimal | None
    max_drawdown: Decimal | None
    trade_count: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BacktestResultDetail(BacktestResultListItem):
    params: dict | None
    initial_capital: Decimal
    annual_return: Decimal | None
    sortino_ratio: Decimal | None
    calmar_ratio: Decimal | None
    win_rate: Decimal | None
    profit_factor: Decimal | None
    avg_holding_period: Decimal | None
    equity_curve: dict | None
    drawdown_curve: dict | None
    trades: dict | None
    monthly_returns: dict | None
    error_message: str | None
    benchmark_return: Decimal | None = None

    model_config = {"from_attributes": True}
