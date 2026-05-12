from dataclasses import dataclass
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    STOPPED = "stopped"


class Market(str, Enum):
    A_STOCK = "a_stock"
    US_STOCK = "us_stock"
    CRYPTO = "crypto"


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
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


@dataclass
class TickData:
    symbol: str
    price: float
    volume: float
    timestamp: str


@dataclass
class OrderInfo:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: float
    price: Optional[float]
    status: str


@dataclass
class TradeInfo:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    timestamp: str


class BaseStrategy(ABC):
    def __init__(self, params: dict):
        self.params = params
        self._context = None

    def set_context(self, context):
        self._context = context

    @abstractmethod
    def on_init(self, context) -> None:
        ...

    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        ...

    def on_tick(self, tick: TickData) -> None:
        pass

    def on_order(self, order: OrderInfo) -> None:
        pass

    def on_trade(self, trade: TradeInfo) -> None:
        pass

    def on_stop(self, context) -> None:
        pass

    def buy(self, symbol: str, qty: float, price: float | None = None) -> str:
        return self._context.send_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            qty=qty,
            price=price,
        )

    def sell(self, symbol: str, qty: float, price: float | None = None) -> str:
        return self._context.send_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            qty=qty,
            price=price,
        )

    def get_position(self, symbol: str) -> float:
        return self._context.get_position(symbol)

    def get_bars(self, symbol: str, length: int) -> list[BarData]:
        return self._context.get_bars(symbol, length)

    def log(self, message: str):
        self._context.log(message)
