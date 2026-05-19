from __future__ import annotations

from decimal import Decimal
from typing import Any

import ccxt.async_support as ccxt
import structlog

from app.services.trade.base import BrokerAdapter, _make_fill_result

logger = structlog.get_logger()

_ORDER_TYPE_MAP = {
    "market": "market",
    "limit": "limit",
    "stop": "stop_market",
}

_SIDE_MAP = {
    "buy": "buy",
    "sell": "sell",
}


class BinanceBroker(BrokerAdapter):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        options: dict[str, Any] | None = None,
    ) -> None:
        self._exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                **(options or {}),
            },
        })
        if testnet:
            self._exchange.set_sandbox_mode(True)
        self._testnet = testnet

    @property
    def market(self) -> str:
        return "crypto"

    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: Decimal,
        price: Decimal | None = None,
    ) -> dict:
        ccxt_symbol = self._normalize_symbol(symbol)
        ccxt_side = _SIDE_MAP.get(side, side)
        ccxt_type = _ORDER_TYPE_MAP.get(order_type, order_type)

        params: dict[str, Any] = {}
        if ccxt_type == "stop_market" and price is not None:
            params["stopPrice"] = float(price)
            ccxt_type = "market"

        try:
            order = await self._exchange.create_order(
                symbol=ccxt_symbol,
                type=ccxt_type,
                side=ccxt_side,
                amount=float(qty),
                price=float(price) if price and ccxt_type == "limit" else None,
                params=params,
            )
        except ccxt.InsufficientFunds as e:
            logger.warning("broker.insufficient_funds", symbol=ccxt_symbol, side=ccxt_side)
            return {"broker_order_id": None, "status": "rejected", "reason": str(e)}
        except ccxt.InvalidOrder as e:
            logger.warning("broker.invalid_order", symbol=ccxt_symbol, error=str(e))
            return {"broker_order_id": None, "status": "rejected", "reason": str(e)}
        except ccxt.BaseError as e:
            logger.error("broker.submit_error", symbol=ccxt_symbol, error=str(e))
            return {"broker_order_id": None, "status": "rejected", "reason": str(e)}

        return self._parse_order(order)

    async def cancel_order(self, broker_order_id: str) -> dict:
        try:
            result = await self._exchange.cancel_order(broker_order_id)
            status = result.get("status", "")
            if status in ("canceled", "cancelled", "expired"):
                return {"status": "cancelled"}
            return {"status": status}
        except ccxt.OrderNotFound:
            return {"status": "not_found"}
        except ccxt.BaseError as e:
            logger.error("broker.cancel_error", order_id=broker_order_id, error=str(e))
            return {"status": "error", "reason": str(e)}

    async def get_order_status(self, broker_order_id: str) -> dict:
        try:
            order = await self._exchange.fetch_order(broker_order_id)
            return self._parse_order(order)
        except ccxt.OrderNotFound:
            return {"status": "not_found"}
        except ccxt.BaseError as e:
            logger.error("broker.status_error", order_id=broker_order_id, error=str(e))
            return {"status": "error", "reason": str(e)}

    async def get_positions(self) -> list[dict]:
        try:
            balance = await self._exchange.fetch_balance()
            positions: list[dict] = []
            for currency, amount in balance.items():
                if currency in ("free", "used", "total", "info", "timestamp", "datetime", "nonce"):
                    continue
                total = amount if isinstance(amount, (int, float)) else amount.get("total", 0)
                if total and float(total) > 0:
                    used = 0
                    if isinstance(amount, dict):
                        used = float(amount.get("used", 0))
                    positions.append({
                        "symbol": currency,
                        "qty": Decimal(str(total)),
                        "used": Decimal(str(used)),
                        "market": "crypto",
                    })
            return positions
        except ccxt.BaseError as e:
            logger.error("broker.positions_error", error=str(e))
            return []

    async def get_account(self) -> dict:
        try:
            balance = await self._exchange.fetch_balance()
            usdt_free = 0.0
            usdt_used = 0.0
            usdt_total = 0.0
            usdt = balance.get("USDT", {})
            if isinstance(usdt, dict):
                usdt_free = float(usdt.get("free", 0))
                usdt_used = float(usdt.get("used", 0))
                usdt_total = float(usdt.get("total", 0))
            elif isinstance(usdt, (int, float)):
                usdt_total = float(usdt)
                usdt_free = float(usdt)
            total_equity = float(balance.get("total", {}).get("USDT", usdt_total))
            return {
                "cash": Decimal(str(usdt_free)),
                "equity": Decimal(str(total_equity)),
                "buying_power": Decimal(str(usdt_free)),
                "currency": "USDT",
            }
        except ccxt.BaseError as e:
            logger.error("broker.account_error", error=str(e))
            return {"cash": Decimal("0"), "equity": Decimal("0"), "buying_power": Decimal("0")}

    async def health_check(self) -> bool:
        try:
            await self._exchange.fetch_time()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        try:
            await self._exchange.close()
        except Exception:
            pass

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        s = symbol.upper().replace("-", "").replace("_", "").replace("/", "")
        if "/" not in s:
            if s.endswith("USDT"):
                return s[:-4] + "/USDT"
            if s.endswith("BUSD"):
                return s[:-4] + "/BUSD"
            if s.endswith("BTC"):
                return s[:-3] + "/BTC"
            if s.endswith("ETH"):
                return s[:-3] + "/ETH"
            if s.endswith("BNB"):
                return s[:-3] + "/BNB"
            return s + "/USDT"
        return s

    @staticmethod
    def _parse_order(order: dict) -> dict:
        status_map = {
            "open": "submitted",
            "new": "submitted",
            "partially_filled": "partial_filled",
            "filled": "filled",
            "closed": "filled",
            "canceled": "cancelled",
            "cancelled": "cancelled",
            "expired": "expired",
            "rejected": "rejected",
        }
        raw_status = order.get("status", "unknown")
        status = status_map.get(raw_status, raw_status)

        result: dict[str, Any] = {
            "broker_order_id": str(order.get("id", "")),
            "status": status,
        }

        filled = order.get("filled")
        if filled is not None:
            result["filled_qty"] = Decimal(str(filled))

        avg_price = order.get("average")
        if avg_price is not None:
            result["filled_price"] = Decimal(str(avg_price))

        cost = order.get("cost")
        fee = order.get("fee")
        if fee and fee.get("cost"):
            result["commission"] = Decimal(str(abs(float(fee["cost"]))))
        elif cost and filled:
            result["commission"] = Decimal(str(float(cost) * 0.001))

        if status == "filled" and filled:
            return _make_fill_result(
                broker_id=result["broker_order_id"],
                qty=Decimal(str(filled)),
                fill_price=Decimal(str(avg_price or order.get("price", 0))),
                commission=result.get("commission", Decimal("0")),
            )

        return result
