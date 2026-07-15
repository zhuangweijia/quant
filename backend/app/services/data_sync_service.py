"""A股数据同步服务 — 从 AKShare 拉取沪深300数据存入 PostgreSQL。

Supports:
- CSI 300 constituent list sync (monthly)
- Daily K-line full/incremental sync (daily)
- Fundamentals sync (weekly)
- Northbound capital flow sync (daily)
- Data integrity validation
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.daily_bar import DailyBar
from app.models.stock import Stock

logger = structlog.get_logger()

_DEFAULT_HISTORY_YEARS = 8
_AKSHARE_DELAY = 0.15  # seconds between AKShare calls


class DataSyncService:
    """Syncs A-share data from AKShare into PostgreSQL."""

    def __init__(self):
        self._failed_symbols: dict[str, str] = {}

    # ── CSI 300 Constituents ──────────────────────────────────────

    async def sync_csi300_constituents(self) -> dict:
        """Sync CSI 300 constituent list. Mark in_csi300 for all stocks."""
        try:
            import akshare as ak
        except ImportError:
            logger.error("data_sync.akshare_not_installed")
            return {"success": False, "error": "akshare not installed"}

        def _fetch():
            df = ak.index_stock_cons_csindex(symbol="000300")
            return df

        try:
            df = await asyncio.to_thread(_fetch)
        except Exception:
            df = await asyncio.to_thread(lambda: ak.index_stock_cons(symbol="000300"))

        async with AsyncSessionLocal() as db:
            existing = await db.execute(select(Stock))
            existing_map = {s.symbol: s for s in existing.scalars().all()}

            new_symbols = set()
            for _, row in df.iterrows():
                symbol = str(row.get("成分券代码", row.iloc[0])).strip()
                name = str(row.get("成分券名称", row.iloc[1] if df.shape[1] > 1 else "")).strip()

                if symbol in existing_map:
                    existing_map[symbol].in_csi300 = True
                    if name:
                        existing_map[symbol].name = name
                else:
                    stock = Stock(symbol=symbol, name=name, in_csi300=True)
                    db.add(stock)
                    new_symbols.add(symbol)

            # Mark stocks no longer in CSI 300
            constituent_symbols = {
                str(r.get("成分券代码", r.iloc[0])).strip() for _, r in df.iterrows()
            }
            for sym, stock in existing_map.items():
                if sym not in constituent_symbols:
                    stock.in_csi300 = False

            await db.commit()

            logger.info("data_sync.constituents_synced", total=df.shape[0], new=len(new_symbols))
            return {"success": True, "total": df.shape[0], "new": len(new_symbols)}

    # ── Daily K-line Sync ─────────────────────────────────────────

    async def sync_daily_bars_full(self, symbol: str, years: int = _DEFAULT_HISTORY_YEARS) -> dict:
        """Full historical K-line sync for one stock via Tencent API (curl fallback)."""
        start_date = (date.today() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")

        rows = await asyncio.to_thread(_fetch_tencent_klines, symbol, start_date, end_date)
        if not rows:
            return {"success": False, "symbol": symbol, "error": "empty or fetch failed"}

        return await self._upsert_tencent_bars(symbol, rows)

    async def sync_daily_bars_incremental(self) -> dict:
        """Incremental sync for all CSI 300 stocks."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Stock).where(Stock.in_csi300.is_(True)))
            stocks = result.scalars().all()

        total = len(stocks)
        success = 0
        failed_list = []

        for i, stock in enumerate(stocks):
            last = stock.last_synced_date
            start = (
                last + timedelta(days=1)
                if last
                else date.today() - timedelta(days=_DEFAULT_HISTORY_YEARS * 365)
            )

            if start >= date.today():
                success += 1
                continue

            result = await self._sync_one_incremental(stock.symbol, start)
            if result["success"]:
                success += 1
                # Update last_synced_date
                async with AsyncSessionLocal() as db:
                    db_stock = await db.get(Stock, stock.id)
                    if db_stock:
                        db_stock.last_synced_date = date.today()
                        await db.commit()
            else:
                failed_list.append(stock.symbol)

            if (i + 1) % 50 == 0:
                logger.info(
                    "data_sync.incremental_progress", done=i + 1, total=total, success=success
                )

        summary = {
            "total": total,
            "success": success,
            "failed": len(failed_list),
            "failed_symbols": failed_list,
        }
        logger.info("data_sync.incremental_complete", **summary)

        # Check failure rate
        if total > 0 and len(failed_list) / total > 0.5:
            await self._publish_sync_alert(len(failed_list), total)

        return summary

    async def _sync_one_incremental(self, symbol: str, start_date: date) -> dict:
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = date.today().strftime("%Y-%m-%d")

            rows = await asyncio.to_thread(_fetch_tencent_klines, symbol, start_str, end_str)
            if not rows:
                return {"success": False, "symbol": symbol, "error": "empty"}
            return await self._upsert_tencent_bars(symbol, rows)
        except Exception as e:
            logger.error("data_sync.incremental_one_failed", symbol=symbol, error=str(e))
            self._failed_symbols[symbol] = str(e)
            return {"success": False, "symbol": symbol, "error": str(e)}

    async def _upsert_daily_bars(self, db_symbol: str, df) -> dict:
        """Upsert DataFrame rows into daily_bars table."""
        if df is None or df.empty:
            return {"success": False, "symbol": db_symbol, "error": "empty"}

        rows = []
        for _, row in df.iterrows():
            trade_date_val = row.get("日期", row.iloc[0])
            if isinstance(trade_date_val, str):
                trade_date_val = datetime.strptime(trade_date_val, "%Y-%m-%d").date()
            elif isinstance(trade_date_val, datetime):
                trade_date_val = trade_date_val.date()

            rows.append(
                {
                    "symbol": db_symbol,
                    "trade_date": trade_date_val,
                    "open": Decimal(str(row.get("开盘", row.iloc[1]))),
                    "high": Decimal(str(row.get("最高", row.iloc[2]))),
                    "low": Decimal(str(row.get("最低", row.iloc[3]))),
                    "close": Decimal(str(row.get("收盘", row.iloc[4]))),
                    "volume": Decimal(str(row.get("成交量", row.iloc[5]))),
                    "amount": Decimal(str(row.get("成交额", 0))) if "成交额" in row else None,
                    "turnover_rate": Decimal(str(row.get("换手率", 0)))
                    if "换手率" in row
                    else None,
                }
            )

        async with AsyncSessionLocal() as db:
            stmt = pg_insert(DailyBar).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_daily_bars_symbol_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "amount": stmt.excluded.amount,
                    "turnover_rate": stmt.excluded.turnover_rate,
                },
            )
            await db.execute(stmt)
            await db.commit()

        return {"success": True, "symbol": db_symbol, "rows": len(rows)}

    async def _upsert_tencent_bars(self, symbol: str, tencent_rows: list[list[str]]) -> dict:
        """Upsert Tencent-format K-line rows into daily_bars table."""
        if not tencent_rows:
            return {"success": False, "symbol": symbol, "error": "empty"}

        rows = []
        for raw in tencent_rows:
            if len(raw) < 6:
                continue
            td = datetime.strptime(raw[0], "%Y-%m-%d").date()
            rows.append(
                {
                    "symbol": symbol,
                    "trade_date": td,
                    "open": Decimal(raw[1]),
                    "high": Decimal(raw[3]),
                    "low": Decimal(raw[4]),
                    "close": Decimal(raw[2]),
                    "volume": Decimal(raw[5]),
                    "amount": None,
                    "turnover_rate": None,
                }
            )

        if not rows:
            return {"success": False, "symbol": symbol, "error": "no valid rows"}

        async with AsyncSessionLocal() as db:
            stmt = pg_insert(DailyBar).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_daily_bars_symbol_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            await db.execute(stmt)
            await db.commit()

        return {"success": True, "symbol": symbol, "rows": len(rows)}

    # ── Fundamentals ──────────────────────────────────────────────

    async def sync_fundamentals(self) -> dict:
        """Weekly fundamentals sync. Caches to Redis."""
        import redis.asyncio as aioredis

        from app.config import get_settings

        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Stock).where(Stock.in_csi300.is_(True)))
                stocks = result.scalars().all()

            success = 0
            for stock in stocks:
                try:
                    data = await self._fetch_fundamentals_one(stock.symbol)
                    if data:
                        await r.setex(
                            f"fundamental:{stock.symbol}",
                            86400,  # 1 day TTL
                            str(data),
                        )
                        success += 1
                    await asyncio.sleep(_AKSHARE_DELAY)
                except Exception as e:
                    logger.warning(
                        "data_sync.fundamental_failed", symbol=stock.symbol, error=str(e)
                    )

            logger.info("data_sync.fundamentals_synced", total=len(stocks), success=success)
            return {"success": True, "total": len(stocks), "cached": success}
        finally:
            await r.aclose()

    async def _fetch_fundamentals_one(self, symbol: str) -> dict | None:
        try:
            import akshare as ak

            def _fetch():
                result = {}
                # PE/PB indicators
                try:
                    df = ak.stock_a_indicator_lg(symbol=symbol)
                    if df is not None and not df.empty:
                        last = df.iloc[-1]
                        result["pe_ttm"] = (
                            float(last.get("pe_ttm", 0)) if last.get("pe_ttm") else None
                        )
                        result["pb"] = float(last.get("pb", 0)) if last.get("pb") else None
                        result["dividend_yield"] = (
                            float(last.get("dv_ratio", 0)) if last.get("dv_ratio") else None
                        )
                        result["ps_ttm"] = (
                            float(last.get("ps_ttm", 0)) if last.get("ps_ttm") else None
                        )
                except Exception:
                    pass

                # Financial abstract
                try:
                    df2 = ak.stock_financial_abstract_ths(symbol=symbol)
                    if df2 is not None and not df2.empty:
                        last = df2.iloc[-1]
                        result.setdefault("roe_ttm", _safe_float(last, "ROE"))
                        result.setdefault("gross_margin", _safe_float(last, "销售毛利率"))
                        result.setdefault("debt_ratio", _safe_float(last, "资产负债率"))
                        result.setdefault("revenue_yoy", _safe_float(last, "营业总收入同比增长率"))
                        result.setdefault("profit_yoy", _safe_float(last, "净利润同比增长率"))
                except Exception:
                    pass

                return result if result else None

            return await asyncio.to_thread(_fetch)
        except Exception:
            return None

    # ── Northbound Capital ────────────────────────────────────────

    async def sync_northbound_flow(self) -> dict:
        """Daily northbound capital flow sync."""
        import redis.asyncio as aioredis

        from app.config import get_settings

        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

        try:
            try:
                import akshare as ak

                def _fetch():
                    return ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")

                df = await asyncio.to_thread(_fetch)
            except Exception as e:
                logger.warning("data_sync.northbound_failed", error=str(e))
                return {"success": False, "error": str(e)}

            if df is None or df.empty:
                return {"success": False, "error": "empty data"}

            count = 0
            for _, row in df.iterrows():
                symbol = str(row.get("股票代码", "")).strip()
                if not symbol:
                    continue
                holding_ratio = _safe_float(row, "持股比例")

                await r.setex(
                    f"northbound:{symbol}",
                    86400,
                    f"{holding_ratio or 0}",
                )
                count += 1

            logger.info("data_sync.northbound_synced", count=count)
            return {"success": True, "count": count}
        finally:
            await r.aclose()

    # ── Data Integrity ────────────────────────────────────────────

    async def validate_data_integrity(self) -> dict:
        """Check for consecutive missing trading days per stock."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Stock).where(Stock.in_csi300.is_(True)))
            stocks = result.scalars().all()

            warnings = 0
            for stock in stocks:
                bars = await db.execute(
                    select(DailyBar.trade_date)
                    .where(DailyBar.symbol == stock.symbol)
                    .order_by(DailyBar.trade_date.desc())
                    .limit(30)
                )
                dates = [r[0] for r in bars.all()]

                if len(dates) < 10:
                    stock.data_quality = "warning"
                    warnings += 1
                    continue

                # Check for gaps > 3 trading days
                max_gap = 0
                for i in range(1, len(dates)):
                    gap = (dates[i - 1] - dates[i]).days
                    if gap > max_gap:
                        max_gap = gap

                if max_gap > 7:  # >7 calendar days ≈ >3 trading days
                    stock.data_quality = "warning"
                    warnings += 1
                else:
                    stock.data_quality = "ok"

            await db.commit()

        logger.info("data_sync.integrity_checked", total=len(stocks), warnings=warnings)
        return {"total": len(stocks), "warnings": warnings}

    # ── Alert ─────────────────────────────────────────────────────

    async def _publish_sync_alert(self, failed: int, total: int):
        try:
            from app.core.events import event_bus

            await event_bus.publish(
                event_bus.TOPIC_DATA_SYNC_ALERT,
                {
                    "failed": failed,
                    "total": total,
                    "rate": failed / total if total > 0 else 0,
                    "message": f"数据同步失败率过高: {failed}/{total}",
                },
            )
        except Exception:
            pass

    # ── Scheduler Registration ────────────────────────────────────

    def register_schedules(self, scheduler):
        """Register APScheduler jobs for periodic data sync."""
        from apscheduler.triggers.cron import CronTrigger

        scheduler.add_job(
            self.sync_daily_bars_incremental,
            trigger=CronTrigger(hour=17, minute=0, timezone="Asia/Shanghai"),
            id="sync_daily_bars",
            replace_existing=True,
        )
        scheduler.add_job(
            self.sync_northbound_flow,
            trigger=CronTrigger(hour=17, minute=30, timezone="Asia/Shanghai"),
            id="sync_northbound",
            replace_existing=True,
        )
        scheduler.add_job(
            self.sync_fundamentals,
            trigger=CronTrigger(day_of_week="sun", hour=2, timezone="Asia/Shanghai"),
            id="sync_fundamentals",
            replace_existing=True,
        )
        scheduler.add_job(
            self.sync_csi300_constituents,
            trigger=CronTrigger(day=1, hour=1, timezone="Asia/Shanghai"),
            id="sync_constituents",
            replace_existing=True,
        )
        scheduler.add_job(
            self.validate_data_integrity,
            trigger=CronTrigger(hour=18, timezone="Asia/Shanghai"),
            id="validate_integrity",
            replace_existing=True,
        )
        logger.info("data_sync.schedules_registered")


def _safe_float(row, key, default=None):
    pass


def _fetch_tencent_klines(symbol: str, start_date: str, end_date: str) -> list[list[str]]:
    """Fetch daily K-line data via Tencent API using curl.

    Returns list of [date, open, close, high, low, volume] strings.
    """
    import json
    import subprocess

    prefix = "sh" if symbol.startswith("6") else "sz"
    ticker = f"{prefix}{symbol}"
    count = 800
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={ticker},day,{start_date},{end_date},{count},qfq"

    try:
        result = subprocess.run(
            ["curl", "-s", "--connect-timeout", "10", "--max-time", "20", url],
            capture_output=True,
            text=True,
            timeout=25,
        )
        if result.returncode != 0 or not result.stdout:
            return []

        data = json.loads(result.stdout)
        stock_data = data.get("data", {}).get(ticker, {})

        for key in ("qfqday", "day"):
            if key in stock_data:
                return stock_data[key]

        return []
    except Exception:
        return []


def _safe_float_legacy(row, key, default=None):
    """Extract a float from a pandas row, handling None/NaN."""
    try:
        val = row.get(key) if hasattr(row, "get") else None
        if val is None or val == "" or (isinstance(val, float) and val != val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


data_sync_service = DataSyncService()
