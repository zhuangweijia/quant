import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import AsyncIterator

import structlog

from app.services.market_service import MarketDataProvider

logger = structlog.get_logger()

_TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
}

_BINANCE_SPOT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    "DOGEUSDT", "XRPUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
]


class BinanceDataProvider(MarketDataProvider):
    def __init__(self):
        self._ccxt = None

    async def _get_client(self):
        if self._ccxt is None:
            import ccxt.async_support as ccxt_async
            self._ccxt = ccxt_async.binance({"enableRateLimit": True})
        return self._ccxt

    async def close(self):
        if self._ccxt:
            await self._ccxt.close()
            self._ccxt = None

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        try:
            client = await self._get_client()
            tf = _TIMEFRAME_MAP.get(timeframe, "1d")
            since = None
            if start:
                d = datetime.fromisoformat(start.replace("Z", "+00:00"))
                since = int(d.timestamp() * 1000)

            ohlcv = await client.fetch_ohlcv(symbol, tf, since=since, limit=min(limit, 500))
            results = []
            for row in ohlcv:
                ts = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc)
                results.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": f"{row[1]:.8f}",
                    "high": f"{row[2]:.8f}",
                    "low": f"{row[3]:.8f}",
                    "close": f"{row[4]:.8f}",
                    "volume": f"{row[5]:.8f}",
                })
            return results
        except Exception as e:
            logger.error("binance.get_klines_failed", symbol=symbol, error=str(e))
            return []

    async def subscribe_ticks(self, symbols: list[str]) -> AsyncIterator[dict]:
        try:
            client = await self._get_client()
            while True:
                tickers = await client.fetch_tickers(symbols[:10])
                for symbol in symbols:
                    ticker = tickers.get(symbol)
                    if ticker:
                        yield {
                            "symbol": symbol,
                            "price": str(ticker.get("last", 0)),
                            "volume": str(ticker.get("quoteVolume", 0)),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                await asyncio.sleep(1)
        except Exception as e:
            logger.error("binance.subscribe_ticks_failed", error=str(e))
            return
            yield

    async def search_symbols(self, keyword: str) -> list[dict]:
        try:
            client = await self._get_client()
            markets = await client.fetch_markets()
            kw = keyword.upper()
            results = []
            for m in markets:
                if m.get("spot") and (kw in (m.get("symbol", "")).upper() or kw in (m.get("base", "")).upper()):
                    results.append({
                        "symbol": m["symbol"],
                        "name": m.get("base", m["symbol"]),
                        "market": "crypto",
                    })
                if len(results) >= 20:
                    break
            return results
        except Exception as e:
            logger.error("binance.search_symbols_failed", error=str(e))
            return []

    async def get_latest_price(self, symbol: str) -> dict:
        try:
            client = await self._get_client()
            ticker = await client.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "price": str(ticker.get("last", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("binance.get_latest_price_failed", symbol=symbol, error=str(e))
            return {"symbol": symbol, "price": "0"}

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            await client.fetch_time()
            return True
        except Exception:
            return False