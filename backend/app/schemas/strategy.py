from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: str | None = Field(None, max_length=1000)
    code: str = Field(..., min_length=1)
    params: dict | None = None
    market: str = Field(..., pattern=r"^(a_stock|us_stock|crypto)$")
    symbol: str | None = Field(None, max_length=32)
    timeframe: str | None = Field(None, pattern=r"^(1m|5m|15m|30m|1h|4h|1d|1w)$")


class StrategyUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=128)
    description: str | None = None
    code: str | None = Field(None, min_length=1)
    params: dict | None = None
    symbol: str | None = Field(None, max_length=32)
    timeframe: str | None = Field(None, pattern=r"^(1m|5m|15m|30m|1h|4h|1d|1w)$")


class StrategyListItem(BaseModel):
    id: UUID
    name: str
    market: str
    status: str
    description: str | None
    symbol: str | None = None
    timeframe: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyDetail(StrategyListItem):
    code: str
    params: dict | None

    model_config = {"from_attributes": True}
