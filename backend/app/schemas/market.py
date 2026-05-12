from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class KlineRequest(BaseModel):
    symbol: str
    market: str
    timeframe: str = "1d"
    start: str | None = None
    end: str | None = None
    limit: int = 500


class KlineData(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    market: str
