from abc import ABC, abstractmethod
from decimal import Decimal

import structlog

logger = structlog.get_logger()


class BrokerAdapter(ABC):
    @property
    @abstractmethod
    def market(self) -> str:
        ...

    @abstractmethod
    async def submit_order(
        self, symbol: str, side: str, order_type: str,
        qty: Decimal, price: Decimal | None = None,
    ) -> dict:
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        ...

    @abstractmethod
    async def get_account(self) -> dict:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


def _make_fill_result(broker_id: str, qty: Decimal, fill_price: Decimal, commission: Decimal) -> dict:
    return {
        "broker_order_id": broker_id,
        "status": "filled",
        "filled_qty": qty,
        "filled_price": fill_price,
        "commission": commission,
    }


class PaperBroker(BrokerAdapter):
    def __init__(self, commission_rate: Decimal = Decimal("0.001"), slippage: Decimal = Decimal("0.001")):
        self._commission_rate = commission_rate
        self._slippage = slippage
        self._orders: dict[str, dict] = {}
        self._counter = 0

    @property
    def market(self) -> str:
        return "paper"

    def _next_id(self) -> str:
        self._counter += 1
        return f"PAPER-{self._counter:06d}"

    async def submit_order(
        self, symbol: str, side: str, order_type: str,
        qty: Decimal, price: Decimal | None = None,
    ) -> dict:
        from app.services.market_service import get_provider
        broker_id = self._next_id()
        provider = get_provider("mock")
        latest = await provider.get_latest_price(symbol)
        market_price = Decimal(latest.get("price", "0"))

        if market_price <= 0:
            return {"broker_order_id": broker_id, "status": "rejected", "reason": "无法获取价格"}

        if order_type == "market":
            if side == "buy":
                fill_price = (market_price * (1 + self._slippage)).quantize(Decimal("0.00000001"))
            else:
                fill_price = (market_price * (1 - self._slippage)).quantize(Decimal("0.00000001"))
            commission = (fill_price * qty * self._commission_rate).quantize(Decimal("0.00000001"))
            self._orders[broker_id] = {
                "status": "filled", "filled_qty": qty,
                "filled_price": fill_price, "commission": commission,
            }
            return _make_fill_result(broker_id, qty, fill_price, commission)

        elif order_type == "limit":
            self._orders[broker_id] = {
                "status": "submitted", "symbol": symbol, "side": side,
                "qty": qty, "limit_price": price, "market_price": market_price,
                "filled_qty": Decimal("0"), "filled_price": None, "commission": Decimal("0"),
            }
            if (side == "buy" and market_price <= price) or (side == "sell" and market_price >= price):
                fill_price = price.quantize(Decimal("0.00000001"))
                commission = (fill_price * qty * self._commission_rate).quantize(Decimal("0.00000001"))
                self._orders[broker_id] = {
                    "status": "filled", "filled_qty": qty,
                    "filled_price": fill_price, "commission": commission,
                }
                return _make_fill_result(broker_id, qty, fill_price, commission)
            return {"broker_order_id": broker_id, "status": "submitted"}

        elif order_type == "stop":
            self._orders[broker_id] = {
                "status": "submitted", "symbol": symbol, "side": side,
                "qty": qty, "stop_price": price, "market_price": market_price,
                "filled_qty": Decimal("0"), "filled_price": None, "commission": Decimal("0"),
            }
            if (side == "sell" and market_price <= price) or (side == "buy" and market_price >= price):
                if side == "sell":
                    fill_price = (price * (1 - self._slippage)).quantize(Decimal("0.00000001"))
                else:
                    fill_price = (price * (1 + self._slippage)).quantize(Decimal("0.00000001"))
                commission = (fill_price * qty * self._commission_rate).quantize(Decimal("0.00000001"))
                self._orders[broker_id] = {
                    "status": "filled", "filled_qty": qty,
                    "filled_price": fill_price, "commission": commission,
                }
                return _make_fill_result(broker_id, qty, fill_price, commission)
            return {"broker_order_id": broker_id, "status": "submitted"}

        return {"broker_order_id": broker_id, "status": "rejected", "reason": "不支持的订单类型"}

    async def cancel_order(self, broker_order_id: str) -> dict:
        order = self._orders.get(broker_order_id)
        if not order:
            return {"status": "not_found"}
        if order["status"] in ("pending", "submitted"):
            order["status"] = "cancelled"
            return {"status": "cancelled"}
        return {"status": order["status"]}

    async def get_order_status(self, broker_order_id: str) -> dict:
        order = self._orders.get(broker_order_id)
        if not order:
            return {"status": "not_found"}
        return {
            "status": order.get("status", "unknown"),
            "filled_qty": order.get("filled_qty", Decimal("0")),
            "filled_price": order.get("filled_price"),
        }

    async def get_positions(self) -> list[dict]:
        return []

    async def get_account(self) -> dict:
        return {"cash": 0, "equity": 0, "buying_power": 0}

    async def health_check(self) -> bool:
        return True


_broker_instance: PaperBroker | None = None


def get_paper_broker() -> PaperBroker:
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = PaperBroker()
    return _broker_instance
