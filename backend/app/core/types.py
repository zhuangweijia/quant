from dataclasses import dataclass
from enum import StrEnum


class Market(StrEnum):
    A_STOCK = "a_stock"


class Timeframe(StrEnum):
    D1 = "1d"
    W1 = "1w"


@dataclass
class BarData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str
