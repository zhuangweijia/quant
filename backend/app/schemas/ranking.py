from decimal import Decimal

from pydantic import BaseModel


class RankingItem(BaseModel):
    rank: int
    symbol: str
    name: str | None = None
    score: Decimal
    label: str | None = None
    rank_change: int | None = None
    confidence: str = "normal"


class RankingResponse(BaseModel):
    date: str
    total: int
    items: list[RankingItem]


class StockDetailResponse(BaseModel):
    symbol: str
    name: str | None = None
    industry: str | None = None
    score: Decimal | None = None
    rank: int | None = None
    label: str | None = None
    confidence: str = "normal"
    explanation: dict | None = None
    fundamentals: dict | None = None
    klines: list[dict] = []
    northbound: dict | None = None


class ScoreHistoryItem(BaseModel):
    date: str
    score: Decimal
    rank: int | None = None
    label: str | None = None


class ScoreHistoryResponse(BaseModel):
    symbol: str
    history: list[ScoreHistoryItem]
