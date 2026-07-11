from dataclasses import dataclass
from enum import Enum


class Market(str, Enum):
    A_STOCK = "a_stock"


class Timeframe(str, Enum):
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
