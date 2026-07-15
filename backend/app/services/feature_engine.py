"""特征工程引擎 — 从 daily_bars 计算因子并存入 stock_factors 表。

Factor categories:
- Momentum: 5/10/20/60d returns, excess return, 12-1 momentum
- Valuation: PE/PB/PS, dividend yield, industry percentiles
- Quality: ROE, gross margin, debt ratio, cashflow ratio
- Growth: revenue/profit YoY, revenue QoQ
- Volume-price: turnover, volatility, vol-price corr, volume ratio
- Technical: RSI, MACD hist, Bollinger position, MA alignment
- Fund flow: northbound holding pct and change
"""

import asyncio
from datetime import date
from decimal import Decimal

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.daily_bar import DailyBar
from app.models.stock import Stock
from app.models.stock_factor import StockFactor

logger = structlog.get_logger()

FACTOR_COLUMNS = [
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "excess_return_20d",
    "momentum_12_1",
    "pe_ttm",
    "pb",
    "ps_ttm",
    "dividend_yield",
    "pe_industry_pct",
    "pb_industry_pct",
    "roe_ttm",
    "gross_margin",
    "debt_ratio",
    "cashflow_to_profit",
    "revenue_yoy",
    "profit_yoy",
    "revenue_qoq",
    "turnover_5d_avg",
    "volatility_20d",
    "vol_price_corr_20d",
    "volume_ratio",
    "rsi_14",
    "macd_hist",
    "boll_position",
    "ma_alignment",
    "northbound_holding_pct",
    "northbound_holding_change",
]


class FeatureEngine:
    """Computes stock factors from daily bars and fundamentals data."""

    # ── Main entry point ──────────────────────────────────────────

    async def compute_all_factors(self, trade_date: date) -> dict:
        """Compute all factors for all CSI 300 stocks on a given date."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Stock).where(Stock.in_csi300.is_(True)))
            stocks = result.scalars().all()

        if not stocks:
            logger.warning("feature_engine.no_csi300_stocks")
            return {"total": 0}

        # Load fundamentals from Redis
        fundamentals = await self._load_fundamentals([s.symbol for s in stocks])

        # Load northbound from Redis
        northbound = await self._load_northbound([s.symbol for s in stocks])

        # Load CSI300 index bars for excess return
        csi300_bars = await self._load_bars(db, "000300", trade_date, 30)

        total = len(stocks)
        computed = 0

        for i, stock in enumerate(stocks):
            try:
                bars = await self._load_bars(db, stock.symbol, trade_date, 260)
                if bars is None or len(bars) < 20:
                    continue

                factors = await asyncio.to_thread(
                    self._compute_factors_for_stock,
                    bars,
                    csi300_bars,
                    stock,
                    fundamentals,
                    northbound,
                )

                if factors:
                    await self._upsert_factors(db, stock.symbol, trade_date, factors)
                    computed += 1

            except Exception as e:
                logger.warning("feature_engine.compute_failed", symbol=stock.symbol, error=str(e))

            if (i + 1) % 50 == 0:
                logger.info("feature_engine.progress", done=i + 1, total=total)

        logger.info(
            "feature_engine.completed", trade_date=str(trade_date), total=total, computed=computed
        )
        return {"total": total, "computed": computed}

    # ── Factor computation (CPU-bound, run in thread) ─────────────

    def _compute_factors_for_stock(
        self,
        bars: pd.DataFrame,
        csi300: pd.DataFrame | None,
        stock: Stock,
        fundamentals: dict,
        northbound: dict,
    ) -> dict:
        """Compute all factors for one stock. bars is indexed by date, has 'close','high','low','open','volume'."""
        factors = {}
        close = bars["close"]
        volume = bars["volume"]

        # ── Momentum ──
        factors["return_5d"] = _pct_change(close, 5)
        factors["return_10d"] = _pct_change(close, 10)
        factors["return_20d"] = _pct_change(close, 20)
        factors["return_60d"] = _pct_change(close, 60)
        factors["momentum_12_1"] = _momentum_12_1(close)

        if csi300 is not None and len(csi300) >= 21:
            stock_20d = _pct_change(close, 20)
            idx_20d = _pct_change(csi300["close"], 20)
            if stock_20d is not None and idx_20d is not None:
                factors["excess_return_20d"] = stock_20d - idx_20d

        # ── Volume-price ──
        if "turnover_rate" in bars.columns:
            factors["turnover_5d_avg"] = _safe(bars["turnover_rate"].rolling(5).mean().iloc[-1])

        returns = close.pct_change().dropna()
        if len(returns) >= 20:
            factors["volatility_20d"] = float(returns.iloc[-20:].std())

            abs_returns = returns.iloc[-20:].abs()
            vol_window = volume.iloc[-20:]
            if len(vol_window) == len(abs_returns) and vol_window.std() > 0:
                factors["vol_price_corr_20d"] = float(vol_window.corr(abs_returns))

        vol_ma20 = volume.rolling(20).mean().iloc[-1]
        if vol_ma20 and vol_ma20 > 0:
            factors["volume_ratio"] = float(volume.iloc[-1] / vol_ma20)

        # ── Technical indicators (pandas-ta) ──
        try:
            import pandas_ta as ta

            rsi = ta.rsi(close, length=14)
            if rsi is not None and not rsi.empty:
                factors["rsi_14"] = _safe(rsi.iloc[-1])

            macd = ta.macd(close, fast=12, slow=26, signal=9)
            if macd is not None and not macd.empty:
                hist_col = [c for c in macd.columns if "MACDh" in c]
                if hist_col:
                    factors["macd_hist"] = _safe(macd[hist_col[0]].iloc[-1])

            bb = ta.bbands(close, length=20, std=2)
            if bb is not None and not bb.empty:
                lower = bb.iloc[-1, 0] if bb.shape[1] > 0 else None
                upper = bb.iloc[-1, 2] if bb.shape[1] > 2 else None
                curr = close.iloc[-1]
                if lower and upper and upper > lower:
                    pos = (curr - lower) / (upper - lower)
                    factors["boll_position"] = max(0.0, min(1.0, float(pos)))

            # MA alignment
            ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else None
            ma10 = close.rolling(10).mean().iloc[-1] if len(close) >= 10 else None
            ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
            curr_close = close.iloc[-1]

            alignment = 0
            chain = [(curr_close, ma5), (ma5, ma10), (ma10, ma20), (ma20, ma60)]
            for fast, slow in chain:
                if fast is not None and slow is not None and fast > slow:
                    alignment += 1
            factors["ma_alignment"] = alignment

        except ImportError:
            logger.debug("feature_engine.pandas_ta_not_installed")
        except Exception as e:
            logger.debug("feature_engine.ta_failed", error=str(e))

        # ── Fundamentals (from cache) ──
        fund = fundamentals.get(stock.symbol, {})
        factors["pe_ttm"] = fund.get("pe_ttm")
        factors["pb"] = fund.get("pb")
        factors["ps_ttm"] = fund.get("ps_ttm")
        factors["dividend_yield"] = fund.get("dividend_yield")
        factors["roe_ttm"] = fund.get("roe_ttm")
        factors["gross_margin"] = fund.get("gross_margin")
        factors["debt_ratio"] = fund.get("debt_ratio")
        factors["revenue_yoy"] = fund.get("revenue_yoy")
        factors["profit_yoy"] = fund.get("profit_yoy")
        factors["revenue_qoq"] = fund.get("revenue_qoq")

        # Cashflow ratio (may not always be available)
        cf = fund.get("cashflow_to_profit")
        factors["cashflow_to_profit"] = cf

        # ── Northbound ──
        nb = northbound.get(stock.symbol, {})
        factors["northbound_holding_pct"] = nb.get("holding_pct")
        factors["northbound_holding_change"] = nb.get("holding_change")

        # Remove None values (keep as NULL in DB)
        return {k: v for k, v in factors.items() if v is not None}

    # ── Factor matrix builder ─────────────────────────────────────

    async def build_factor_matrix(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Build a training factor matrix with cross-sectional preprocessing."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(StockFactor)
                .where(StockFactor.trade_date >= start_date, StockFactor.trade_date <= end_date)
                .order_by(StockFactor.trade_date, StockFactor.symbol)
            )
            rows = result.scalars().all()

        if not rows:
            logger.warning("feature_engine.no_factor_data")
            return pd.DataFrame()

        # Build DataFrame
        records = []
        for r in rows:
            row = {"symbol": r.symbol, "trade_date": r.trade_date}
            for col in FACTOR_COLUMNS:
                val = getattr(r, col, None)
                row[col] = float(val) if val is not None else None
            records.append(row)

        df = pd.DataFrame(records)
        df = df.set_index(["trade_date", "symbol"])

        # Cross-sectional preprocessing per trade_date
        factor_df = df[FACTOR_COLUMNS]

        # Group by trade_date and standardize
        grouped = factor_df.groupby(level="trade_date")

        # Z-score standardization
        standardized = grouped.transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else x * 0
        )

        # Fill NaN with cross-sectional median
        standardized = grouped.transform(lambda x: x.fillna(x.median()))

        # Winsorize at ±3σ
        standardized = standardized.clip(-3, 3)

        # Fill remaining NaN (entire column was NaN for that date) with 0
        standardized = standardized.fillna(0)

        return standardized

    def get_factor_names(self) -> list[str]:
        return list(FACTOR_COLUMNS)

    # ── Helpers ───────────────────────────────────────────────────

    async def _load_bars(self, db, symbol: str, end_date: date, count: int) -> pd.DataFrame | None:
        """Load daily bars for a symbol up to end_date."""
        result = await db.execute(
            select(DailyBar)
            .where(DailyBar.symbol == symbol, DailyBar.trade_date <= end_date)
            .order_by(DailyBar.trade_date.desc())
            .limit(count)
        )
        bars = result.scalars().all()
        if not bars:
            return None

        records = []
        for b in reversed(bars):
            records.append(
                {
                    "date": b.trade_date,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": float(b.volume),
                    "turnover_rate": float(b.turnover_rate) if b.turnover_rate else None,
                }
            )

        df = pd.DataFrame(records)
        df = df.set_index("date")
        return df

    async def _load_fundamentals(self, symbols: list[str]) -> dict:
        """Load fundamentals from Redis cache."""
        import json

        import redis.asyncio as aioredis

        from app.config import get_settings

        result = {}
        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        try:
            for sym in symbols:
                raw = await r.get(f"fundamental:{sym}")
                if raw:
                    try:
                        # Handle both JSON and Python repr strings
                        raw = raw.strip()
                        if raw.startswith("{"):
                            result[sym] = json.loads(raw)
                        else:
                            # Try ast.literal_eval for Python dict repr
                            import ast

                            result[sym] = ast.literal_eval(raw)
                    except Exception:
                        pass
        finally:
            await r.aclose()
        return result

    async def _load_northbound(self, symbols: list[str]) -> dict:
        """Load northbound holding from Redis."""
        import redis.asyncio as aioredis

        from app.config import get_settings

        result = {}
        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        try:
            for sym in symbols:
                raw = await r.get(f"northbound:{sym}")
                if raw:
                    try:
                        result[sym] = {"holding_pct": float(raw)}
                    except ValueError:
                        pass

                # Check for previous day's value for change calculation
                prev = await r.get(f"northbound_prev:{sym}")
                if raw and prev:
                    try:
                        change = float(raw) - float(prev)
                        result.setdefault(sym, {})["holding_change"] = change
                    except ValueError:
                        pass
        finally:
            await r.aclose()
        return result

    async def _upsert_factors(self, db, symbol: str, trade_date: date, factors: dict):
        """Upsert factors into stock_factors table."""
        # Convert float values to Decimal
        clean = {}
        for k, v in factors.items():
            if v is not None and v == v:  # not NaN
                clean[k] = Decimal(str(round(v, 6)))

        stmt = pg_insert(StockFactor).values(symbol=symbol, trade_date=trade_date, **clean)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_stock_factors_symbol_date",
            set_=clean,
        )
        await db.execute(stmt)
        await db.flush()


# ── Utility functions ────────────────────────────────────────────


def _pct_change(series, periods: int):
    """Safe percentage change over N periods."""
    if len(series) <= periods:
        return None
    val = series.iloc[-1]
    prev = series.iloc[-(periods + 1)]
    if prev and prev != 0:
        return float((val / prev) - 1)
    return None


def _momentum_12_1(close):
    """12-month momentum skipping most recent month."""
    if len(close) <= 252:
        return None
    t21 = close.iloc[-21]
    t252 = close.iloc[-253] if len(close) > 252 else close.iloc[0]
    if t252 and t252 != 0:
        return float((t21 / t252) - 1)
    return None


def _safe(val):
    """Convert pandas/numpy value to float or None."""
    if val is None:
        return None
    try:
        import numpy as np

        if isinstance(val, (np.integer,)):
            return float(val)
        if isinstance(val, (np.floating,)):
            return float(val) if val == val else None  # NaN check
        if isinstance(val, float):
            return val if val == val else None
        return float(val)
    except (ValueError, TypeError):
        return None
