from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_equity: Decimal
    cash: Decimal
    position_value: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    running_strategies: int
    total_strategies: int
    today_trades: int
    unread_alerts: int


class EquityCurvePoint(BaseModel):
    date: str
    equity: float
    benchmark: float | None = None


class StrategyRankItem(BaseModel):
    strategy_id: UUID
    name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    trade_count: int
    status: str
