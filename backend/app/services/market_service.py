import asyncio
import random
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.util import find_spec

import structlog

logger = structlog.get_logger()


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 500,
    ) -> list[dict]: ...

    @abstractmethod
    async def subscribe_ticks(self, symbols: list[str]) -> AsyncIterator[dict]: ...

    @abstractmethod
    async def search_symbols(self, keyword: str) -> list[dict]: ...

    @abstractmethod
    async def get_latest_price(self, symbol: str) -> dict: ...

    @abstractmethod
    async def health_check(self) -> bool: ...


class MockDataProvider(MarketDataProvider):
    _SYMBOLS = {
        "BTCUSDT": {"name": "Bitcoin", "market": "crypto", "base_price": 65000},
        "ETHUSDT": {"name": "Ethereum", "market": "crypto", "base_price": 3500},
        "BNBUSDT": {"name": "BNB", "market": "crypto", "base_price": 600},
        "SOLUSDT": {"name": "Solana", "market": "crypto", "base_price": 170},
        "ADAUSDT": {"name": "Cardano", "market": "crypto", "base_price": 0.45},
        "DOGEUSDT": {"name": "Dogecoin", "market": "crypto", "base_price": 0.12},
        "XRPUSDT": {"name": "Ripple", "market": "crypto", "base_price": 0.55},
        "AAPL": {"name": "Apple Inc.", "market": "us_stock", "base_price": 189},
        "GOOGL": {"name": "Alphabet Inc.", "market": "us_stock", "base_price": 175},
        "MSFT": {"name": "Microsoft Corp.", "market": "us_stock", "base_price": 420},
        "AMZN": {"name": "Amazon.com Inc.", "market": "us_stock", "base_price": 185},
        "TSLA": {"name": "Tesla Inc.", "market": "us_stock", "base_price": 245},
        "NVDA": {"name": "NVIDIA Corp.", "market": "us_stock", "base_price": 900},
        "META": {"name": "Meta Platforms", "market": "us_stock", "base_price": 500},
        "600519": {"name": "贵州茅台", "market": "a_stock", "base_price": 1700},
        "000001": {"name": "平安银行", "market": "a_stock", "base_price": 12},
        "601318": {"name": "中国平安", "market": "a_stock", "base_price": 45},
        "000858": {"name": "五粮液", "market": "a_stock", "base_price": 150},
        "600036": {"name": "招商银行", "market": "a_stock", "base_price": 35},
        "601012": {"name": "隆基绿能", "market": "a_stock", "base_price": 22},
    }

    def _tf_to_minutes(self, timeframe: str) -> int:
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080,
        }
        return mapping.get(timeframe, 1440)

    def _generate_klines(
        self, symbol: str, timeframe: str, start: datetime, count: int
    ) -> list[dict]:
        info = self._SYMBOLS.get(symbol)
        if not info:
            return []
        base = info["base_price"]
        minutes = self._tf_to_minutes(timeframe)
        klines = []
        price = base * (1 + random.uniform(-0.1, 0.1))
        for i in range(count):
            ts = start + timedelta(minutes=minutes * i)
            change = random.uniform(-0.02, 0.02)
            open_p = price
            close_p = price * (1 + change)
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.01))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.01))
            volume = random.uniform(100, 10000)
            klines.append(
                {
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": f"{open_p:.8f}",
                    "high": f"{high_p:.8f}",
                    "low": f"{low_p:.8f}",
                    "close": f"{close_p:.8f}",
                    "volume": f"{volume:.8f}",
                }
            )
            price = close_p
        return klines

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        if start:
            st = datetime.strptime(start, "%Y-%m-%d")
        else:
            st = datetime.now(UTC) - timedelta(days=limit)
        return self._generate_klines(symbol, timeframe, st, min(limit, 500))

    async def subscribe_ticks(self, symbols: list[str]) -> AsyncIterator[dict]:
        while True:
            import asyncio

            await asyncio.sleep(1)
            for symbol in symbols:
                info = self._SYMBOLS.get(symbol)
                if info:
                    base = info["base_price"]
                    price = base * (1 + random.uniform(-0.005, 0.005))
                    yield {
                        "symbol": symbol,
                        "price": f"{price:.8f}",
                        "volume": f"{random.uniform(1, 100):.8f}",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }

    async def search_symbols(self, keyword: str) -> list[dict]:
        kw = keyword.upper()
        results = []
        for sym, info in self._SYMBOLS.items():
            if kw in sym.upper() or kw in info["name"].upper():
                results.append(
                    {
                        "symbol": sym,
                        "name": info["name"],
                        "market": info["market"],
                    }
                )
        return results[:20]

    async def get_latest_price(self, symbol: str) -> dict:
        info = self._SYMBOLS.get(symbol)
        if not info:
            return {"symbol": symbol, "price": "0", "timestamp": datetime.now(UTC).isoformat()}
        base = info["base_price"]
        price = base * (1 + random.uniform(-0.005, 0.005))
        return {
            "symbol": symbol,
            "price": f"{price:.8f}",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def health_check(self) -> bool:
        return True


class AKShareProvider(MarketDataProvider):
    def __init__(self):
        try:
            import akshare as ak

            self._ak = ak
        except ImportError:
            self._ak = None

    async def get_klines(self, symbol, timeframe, start=None, end=None, limit=500):
        if not self._ak:
            return []
        try:
            import asyncio

            return await asyncio.to_thread(
                self._get_klines_sync, symbol, timeframe, start, end, limit
            )
        except Exception as e:
            logger.error("akshare.get_klines_failed", error=str(e))
            return []

    def _get_klines_sync(self, symbol, timeframe, start, end, limit):
        ak = self._ak
        end_date = end or datetime.now().strftime("%Y%m%d")
        start_date = start or (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        period = "daily" if timeframe in ("1d", "1w") else timeframe
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust="qfq"
            )
        except Exception:
            return []
        df = df.tail(limit)
        results = []
        for _, row in df.iterrows():
            results.append(
                {
                    "timestamp": str(row.get("日期", row.iloc[0])),
                    "open": f"{row.get('开盘', row.iloc[1]):.8f}",
                    "high": f"{row.get('最高', row.iloc[2]):.8f}",
                    "low": f"{row.get('最低', row.iloc[3]):.8f}",
                    "close": f"{row.get('收盘', row.iloc[4]):.8f}",
                    "volume": f"{row.get('成交量', row.iloc[5]):.8f}",
                }
            )
        return results

    async def subscribe_ticks(self, symbols):
        return
        yield

    async def search_symbols(self, keyword):
        if not self._ak:
            return []
        try:
            import asyncio

            return await asyncio.to_thread(self._search_sync, keyword)
        except Exception as e:
            logger.error("akshare.search_failed", error=str(e))
            return []

    def _search_sync(self, keyword):
        ak = self._ak
        try:
            df = ak.stock_zh_a_spot_em()
            mask = df["名称"].str.contains(keyword, case=False, na=False) | df["代码"].str.contains(
                keyword, case=False, na=False
            )
            df = df[mask].head(20)
            return [
                {"symbol": str(r["代码"]), "name": str(r["名称"]), "market": "a_stock"}
                for _, r in df.iterrows()
            ]
        except Exception:
            return []

    async def get_latest_price(self, symbol):
        if not self._ak:
            return {"symbol": symbol, "price": "0"}
        try:
            import asyncio

            return await asyncio.to_thread(self._get_price_sync, symbol)
        except Exception:
            return {"symbol": symbol, "price": "0"}

    def _get_price_sync(self, symbol):
        ak = self._ak
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol].iloc[0]
            return {
                "symbol": symbol,
                "price": f"{row['最新价']:.8f}",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception:
            return {"symbol": symbol, "price": "0"}

    async def health_check(self):
        return self._ak is not None


_providers: dict[str, MarketDataProvider] = {}


def get_provider(market: str) -> MarketDataProvider:
    if market in _providers:
        return _providers[market]
    if market == "a_stock":
        if find_spec("akshare") is None:
            logger.warning("akshare.not_installed")
        else:
            try:
                provider = AKShareProvider()
                _providers[market] = provider
                return provider
            except ImportError:
                logger.warning("akshare.not_installed")
    provider = MockDataProvider()
    _providers[market] = provider
    return provider


async def get_cached_prices(
    symbols: list[tuple[str, str]],
) -> dict[str, Decimal]:
    import redis.asyncio as aioredis

    from app.config import get_settings

    if not symbols:
        return {}

    settings = get_settings()
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        keys = [f"price:{market}:{sym}" for sym, market in symbols]
        cached = await r.mget(keys)
        result: dict[str, Decimal] = {}
        miss_indices: list[int] = []

        for i, (sym, market) in enumerate(symbols):
            if cached[i] is not None:
                result[sym] = Decimal(cached[i])
            else:
                miss_indices.append(i)

        if not miss_indices:
            return result

        miss_by_market: dict[str, list[tuple[int, str]]] = {}
        for idx in miss_indices:
            sym, market = symbols[idx]
            miss_by_market.setdefault(market, []).append((idx, sym))

        a_stock_symbols: list[tuple[int, str]] = miss_by_market.pop("a_stock", [])
        if a_stock_symbols:
            prices = await _batch_akshare_prices([sym for _, sym in a_stock_symbols])
            for idx, sym in a_stock_symbols:
                price = prices.get(sym, Decimal("0"))
                result[sym] = price
                await r.set(f"price:a_stock:{sym}", str(price), ex=30)

        for market, items in miss_by_market.items():
            tasks = []
            for idx, sym in items:
                provider = get_provider(market)
                tasks.append((idx, sym, provider))
            fetch_results = await asyncio.gather(
                *[_safe_get_price(provider, sym) for _, sym, provider in tasks],
                return_exceptions=True,
            )
            for (idx, sym, _), price_val in zip(tasks, fetch_results):
                price = price_val if isinstance(price_val, Decimal) else Decimal("0")
                result[sym] = price
                await r.set(f"price:{market}:{sym}", str(price), ex=30)

        return result
    finally:
        await r.aclose()


async def _safe_get_price(provider: MarketDataProvider, symbol: str) -> Decimal:
    try:
        latest = await provider.get_latest_price(symbol)
        return Decimal(latest.get("price", "0"))
    except Exception:
        return Decimal("0")


async def _batch_akshare_prices(symbols: list[str]) -> dict[str, Decimal]:
    if not symbols:
        return {}
    try:
        import akshare as ak

        def _fetch() -> dict[str, str]:
            df = ak.stock_zh_a_spot_em()
            result = {}
            for sym in symbols:
                row = df[df["代码"] == sym]
                if not row.empty:
                    result[sym] = str(row.iloc[0]["最新价"])
            return result

        prices_raw = await asyncio.to_thread(_fetch)
        return {sym: Decimal(val) for sym, val in prices_raw.items()}
    except Exception as e:
        logger.error("market.akshare_batch_failed", error=str(e))
        return {}
