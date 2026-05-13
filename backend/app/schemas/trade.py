from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    market: str = Field(..., pattern=r"^(a_stock|us_stock|crypto)$")
    side: str = Field(..., pattern=r"^(buy|sell)$")
    order_type: str = Field(..., pattern=r"^(market|limit|stop)$")
    qty: Decimal = Field(..., gt=0)
    price: Decimal | None = None
    strategy_id: UUID | None = None


class OrderResponse(BaseModel):
    id: UUID
    strategy_id: UUID | None
    symbol: str
    market: str
    side: str
    order_type: str
    qty: Decimal
    price: Decimal | None
    status: str
    filled_qty: Decimal
    filled_price: Decimal | None
    commission: Decimal
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
    id: UUID
    strategy_id: UUID | None
    symbol: str
    market: str
    qty: Decimal
    avg_price: Decimal
    frozen_qty: Decimal = Decimal("0")
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountInfoResponse(BaseModel):
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
    mode: str

    model_config = {"from_attributes": True}
