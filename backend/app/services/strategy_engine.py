import asyncio
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.types import BaseStrategy, BarData, OrderSide, OrderType
from app.models.strategy import Strategy
from app.models.strategy_log import StrategyLog

logger = structlog.get_logger()

BLOCKED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "ctypes",
    "importlib", "signal", "multiprocessing", "threading",
    "pathlib", "glob", "tempfile", "pickle", "shelve",
    "webbrowser", "antigravity", "http", "urllib", "ftplib",
    "smtplib", "telnetlib", "xmlrpc",
}


class StrategyContext:
    def __init__(self, engine: "StrategyEngine", strategy_id: str, user_id: str, strategy: BaseStrategy):
        self._engine = engine
        self._strategy_id = strategy_id
        self._user_id = user_id
        self._strategy = strategy
        self._bars_cache: dict[str, list[BarData]] = {}

    def send_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                   qty: float, price: float | None = None) -> str:
        try:
            from app.database import AsyncSessionLocal
            from app.services.trade.order_manager import submit_order
            from app.services.risk_service import evaluate_risk
            from sqlalchemy.util import greenlet_spawn

            async def _do():
                order_data = {
                    "symbol": symbol,
                    "market": "crypto",
                    "side": side.value,
                    "order_type": order_type.value,
                    "qty": Decimal(str(qty)),
                    "price": Decimal(str(price)) if price else None,
                    "strategy_id": self._strategy_id,
                }
                async with AsyncSessionLocal() as db:
                    passed, reason = await evaluate_risk(db, self._user_id, order_data)
                    if not passed:
                        await self._engine._log(self._strategy_id, self._user_id, "WARNING", f"风控拦截: {reason}")
                        return ""
                    try:
                        order = await submit_order(db, self._user_id, order_data)
                        await db.commit()
                        return str(order.id)
                    except Exception as e:
                        await self._engine._log(self._strategy_id, self._user_id, "ERROR", f"下单失败: {e}")
                        return ""

            return greenlet_spawn(_do)
        except Exception as e:
            logger.error("strategy.send_order_failed", error=str(e))
            return ""

    def get_position(self, symbol: str) -> float:
        try:
            from app.database import AsyncSessionLocal
            from app.models.position import Position
            from sqlalchemy.util import greenlet_spawn

            async def _do():
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Position).where(
                            Position.user_id == self._user_id,
                            Position.symbol == symbol,
                        )
                    )
                    pos = result.scalar_one_or_none()
                    return float(pos.qty) if pos else 0.0

            return greenlet_spawn(_do)
        except Exception:
            return 0.0

    def get_bars(self, symbol: str, length: int) -> list[BarData]:
        return self._bars_cache.get(symbol, [])[-length:]

    def log(self, message: str):
        try:
            asyncio.ensure_future(
                self._engine._log(self._strategy_id, self._user_id, "INFO", message)
            )
        except Exception:
            pass


async def _risk_check_job():
    try:
        from app.database import AsyncSessionLocal
        from app.models.account import Account
        from app.services.risk_service import check_stop_loss_take_profit

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Account))
            accounts = result.scalars().all()
            for account in accounts:
                try:
                    await check_stop_loss_take_profit(db, account.user_id)
                    await db.commit()
                except Exception as e:
                    logger.error("risk_check.account_failed", user_id=account.user_id, error=str(e))
                    await db.rollback()
    except Exception as e:
        logger.error("risk_check_job.failed", error=str(e))


class StrategyEngine:
    def __init__(self):
        self._instances: dict[str, dict] = {}
        self._scheduler = AsyncIOScheduler()
        self._started = False

    def start(self):
        if not self._started:
            self._scheduler.start()
            self._started = True
            self._scheduler.add_job(
                _risk_check_job,
                trigger=IntervalTrigger(minutes=1),
                id="risk_stop_loss_take_profit",
                replace_existing=True,
            )
            logger.info("strategy_engine.started")

    def stop(self):
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("strategy_engine.stopped")

    _SAFE_BUILTINS = {
        "len": len, "range": range, "min": min, "max": max, "abs": abs,
        "round": round, "sum": sum, "enumerate": enumerate, "zip": zip,
        "map": map, "filter": filter, "sorted": sorted, "reversed": reversed,
        "isinstance": isinstance, "float": float, "int": int, "str": str,
        "list": list, "dict": dict, "tuple": tuple, "set": set, "bool": bool,
        "print": print, "None": None, "True": True, "False": False,
    }

    def _load_strategy_class(self, code: str) -> type[BaseStrategy]:
        restricted_globals = {
            "__builtins__": self._SAFE_BUILTINS,
            "BaseStrategy": BaseStrategy,
            "BarData": BarData,
            "Decimal": Decimal,
        }

        _safe_import = __builtins__.get("__import__") if isinstance(__builtins__, dict) else getattr(__builtins__, "__import__", None)

        def _restricted_import(name, *args, **kwargs):
            if name in BLOCKED_MODULES:
                raise ImportError(f"Module '{name}' is blocked for security reasons")
            return (_safe_import or __import__)(name, *args, **kwargs)

        restricted_globals["__builtins__"] = restricted_globals | {"__import__": _restricted_import}

        exec_namespace = {}
        try:
            exec(code, restricted_globals, exec_namespace)
        except Exception as e:
            raise ValueError(f"策略代码执行错误: {e}")

        strategy_cls = None
        for obj in exec_namespace.values():
            if isinstance(obj, type) and issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                strategy_cls = obj
                break

        if strategy_cls is None:
            raise ValueError("未找到 BaseStrategy 子类")

        return strategy_cls

    async def start_strategy(self, strategy_id: str, user_id: str, code: str, params: dict, market: str, timeframe: str, symbol: str = "BTCUSDT"):
        if strategy_id in self._instances:
            await self.stop_strategy(strategy_id)

        try:
            strategy_cls = self._load_strategy_class(code)
        except ValueError as e:
            await self._log(strategy_id, user_id, "ERROR", str(e))
            raise

        strategy_instance = strategy_cls(params or {})
        context = StrategyContext(self, strategy_id, user_id, strategy_instance)
        strategy_instance.set_context(context)

        try:
            strategy_instance.on_init(context)
        except Exception as e:
            await self._log(strategy_id, user_id, "ERROR", f"策略初始化失败: {e}")
            raise

        tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        interval = tf_minutes.get(timeframe, 1440)

        job = self._scheduler.add_job(
            self._on_bar_tick,
            trigger=IntervalTrigger(minutes=interval),
            id=f"strategy_{strategy_id}",
            args=[strategy_id, user_id, market, timeframe],
            replace_existing=True,
        )

        self._instances[strategy_id] = {
            "instance": strategy_instance,
            "context": context,
            "user_id": user_id,
            "market": market,
            "timeframe": timeframe,
            "symbol": symbol,
            "job": job,
        }

        await self._log(strategy_id, user_id, "INFO", f"策略已启动，周期: {timeframe}")
        logger.info("strategy_engine.strategy_started", strategy_id=strategy_id)

    async def stop_strategy(self, strategy_id: str):
        info = self._instances.pop(strategy_id, None)
        if info:
            try:
                info["instance"].on_stop(info["context"])
            except Exception:
                pass
            try:
                self._scheduler.remove_job(f"strategy_{strategy_id}")
            except Exception:
                pass
            await self._log(strategy_id, info["user_id"], "INFO", "策略已停止")
            logger.info("strategy_engine.strategy_stopped", strategy_id=strategy_id)

    async def _on_bar_tick(self, strategy_id: str, user_id: str, market: str, timeframe: str):
        info = self._instances.get(strategy_id)
        if not info:
            return

        instance = info["instance"]
        context = info["context"]

        try:
            from app.services.market_service import get_provider
            provider = get_provider(market)
            symbol = info.get("symbol", "BTCUSDT")
            klines = await provider.get_klines(symbol, timeframe, limit=1)

            if klines:
                bar_data = BarData(
                    symbol=symbol,
                    open=float(klines[-1]["open"]),
                    high=float(klines[-1]["high"]),
                    low=float(klines[-1]["low"]),
                    close=float(klines[-1]["close"]),
                    volume=float(klines[-1]["volume"]),
                    timestamp=klines[-1]["timestamp"],
                )

                if bar_data.symbol not in context._bars_cache:
                    context._bars_cache[bar_data.symbol] = []
                context._bars_cache[bar_data.symbol].append(bar_data)
                if len(context._bars_cache[bar_data.symbol]) > 500:
                    context._bars_cache[bar_data.symbol] = context._bars_cache[bar_data.symbol][-500:]

                instance.on_bar(bar_data)

        except Exception as e:
            await self._log(strategy_id, user_id, "ERROR", f"策略执行异常: {e}")
            logger.error("strategy_engine.execution_error", strategy_id=strategy_id, error=str(e))

    async def _log(self, strategy_id: str, user_id: str, level: str, message: str):
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                log_entry = StrategyLog(
                    strategy_id=strategy_id,
                    user_id=user_id,
                    level=level,
                    message=message,
                )
                db.add(log_entry)
                await db.commit()

                try:
                    from app.core.events import event_bus
                    await event_bus.publish("strategy:log", {
                        "strategy_id": strategy_id,
                        "user_id": user_id,
                        "level": level,
                        "message": message,
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error("strategy_engine.log_failed", error=str(e))

    def is_running(self, strategy_id: str) -> bool:
        return strategy_id in self._instances


strategy_engine = StrategyEngine()
