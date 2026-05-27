import structlog

from app.services.trade.base import BrokerAdapter

logger = structlog.get_logger()


class AlpacaBroker(BrokerAdapter):
    def __init__(self, api_key: str, api_secret: str, base_url: str | None = None):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url or "https://paper-api.alpaca.markets"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from alpaca.trading.client import TradingClient
                self._client = TradingClient(
                    api_key=self._api_key,
                    secret_key=self._api_secret,
                    paper=True,
                )
            except ImportError:
                logger.error("alpaca.not_installed")
                return None
        return self._client

    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: float | None = None,
        strategy_id: str | None = None,
    ) -> str:
        client = self._get_client()
        if not client:
            raise RuntimeError("Alpaca client not available")
        import asyncio
        return await asyncio.to_thread(
            self._submit_order_sync, symbol, side, order_type, qty, price
        )

    def _submit_order_sync(self, symbol, side, order_type, qty, price):
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        side_enum = OrderSide.BUY if side == "buy" else OrderSide.SELL

        if order_type == "market":
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=TimeInForce.GTC,
            )
        else:
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                limit_price=price,
                time_in_force=TimeInForce.GTC,
            )

        resp = self._client.submit_order(request)
        return resp.id

    async def cancel_order(self, order_id: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        import asyncio
        try:
            await asyncio.to_thread(self._client.cancel_order_by_id, order_id)
            return True
        except Exception as e:
            logger.error("alpaca.cancel_failed", order_id=order_id, error=str(e))
            return False

    async def get_order_status(self, order_id: str) -> dict:
        client = self._get_client()
        if not client:
            return {"status": "unknown"}
        import asyncio
        try:
            order = await asyncio.to_thread(self._client.get_order_by_id, order_id)
            return {
                "order_id": str(order.id),
                "status": str(order.status).lower(),
                "filled_qty": float(order.filled_qty or 0),
                "filled_price": float(order.filled_avg_price or 0),
            }
        except Exception as e:
            logger.error("alpaca.get_order_failed", order_id=order_id, error=str(e))
            return {"status": "unknown"}

    async def get_positions(self) -> list[dict]:
        client = self._get_client()
        if not client:
            return []
        import asyncio
        try:
            positions = await asyncio.to_thread(self._client.get_all_positions)
            return [{
                "symbol": p.symbol,
                "qty": float(p.qty),
                "avg_price": float(p.avg_entry_price),
                "current_price": float(p.current_price or 0),
                "unrealized_pnl": float(p.unrealized_pl or 0),
            } for p in positions]
        except Exception as e:
            logger.error("alpaca.get_positions_failed", error=str(e))
            return []

    async def get_account(self) -> dict:
        client = self._get_client()
        if not client:
            return {"cash": 0}
        import asyncio
        try:
            acc = await asyncio.to_thread(self._client.get_account)
            return {
                "cash": float(acc.cash),
                "portfolio_value": float(acc.portfolio_value or 0),
                "equity": float(acc.equity or 0),
            }
        except Exception as e:
            logger.error("alpaca.get_account_failed", error=str(e))
            return {"cash": 0}

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            if not client:
                return False
            import asyncio
            acc = await asyncio.to_thread(client.get_account)
            return acc is not None
        except Exception:
            return False