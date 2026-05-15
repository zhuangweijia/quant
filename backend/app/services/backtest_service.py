import asyncio
import math
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import BacktestResult
from app.models.strategy import Strategy
from app.services.market_service import get_provider
from app.core.types import BaseStrategy, BarData, OrderSide, OrderType
import structlog

logger = structlog.get_logger()


_SAFE_BUILTINS = {
    "len": len, "range": range, "min": min, "max": max, "abs": abs,
    "round": round, "sum": sum, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "sorted": sorted, "reversed": reversed,
    "isinstance": isinstance, "float": float, "int": int, "str": str,
    "list": list, "dict": dict, "tuple": tuple, "set": set, "bool": bool,
    "print": print, "None": None, "True": True, "False": False,
}


def _load_strategy_class(code: str) -> type[BaseStrategy]:
    restricted_globals = {
        "__builtins__": _SAFE_BUILTINS,
        "BaseStrategy": BaseStrategy,
        "BarData": BarData,
        "Decimal": Decimal,
    }

    exec_namespace = {}
    exec(code, restricted_globals, exec_namespace)

    for obj in exec_namespace.values():
        if isinstance(obj, type) and issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
            return obj
    raise ValueError("未找到 BaseStrategy 子类")


class BacktestContext:
    def __init__(self, initial_cash: float, commission_rate: float, slippage: float, market: str):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.market = market
        self.positions: dict[str, dict] = {}
        self.orders: list[dict] = []
        self.bars_cache: dict[str, list[BarData]] = {}
        self.equity_curve: list[dict] = []
        self.trades: list[dict] = []
        self.current_price: float = 0

    def send_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                   qty: float, price: float | None = None) -> str:
        import uuid
        order_id = str(uuid.uuid4())[:8]

        if side == OrderSide.BUY:
            fill_price = (price if price else self.current_price) * (1 + self.slippage)
            commission = fill_price * qty * self.commission_rate
            cost = fill_price * qty + commission
            if cost > self.cash:
                return ""
            self.cash -= cost

            if symbol in self.positions:
                pos = self.positions[symbol]
                new_qty = pos["qty"] + qty
                pos["avg_price"] = (pos["avg_price"] * pos["qty"] + fill_price * qty) / new_qty
                pos["qty"] = new_qty
            else:
                self.positions[symbol] = {"qty": qty, "avg_price": fill_price}

            self.trades.append({
                "entry_time": None,
                "exit_time": None,
                "symbol": symbol,
                "side": "buy",
                "entry_price": round(fill_price, 2),
                "exit_price": None,
                "qty": round(qty, 6),
                "pnl": None,
            })

        elif side == OrderSide.SELL:
            pos = self.positions.get(symbol)
            if not pos or pos["qty"] < qty:
                return ""

            fill_price = (price if price else self.current_price) * (1 - self.slippage)
            commission = fill_price * qty * self.commission_rate
            proceeds = fill_price * qty - commission
            self.cash += proceeds

            pnl = proceeds - (pos["avg_price"] * qty)
            pos["qty"] -= qty
            if pos["qty"] <= 0:
                del self.positions[symbol]

            self.trades.append({
                "entry_time": None,
                "exit_time": None,
                "symbol": symbol,
                "side": "sell",
                "entry_price": round(pos["avg_price"], 2),
                "exit_price": round(fill_price, 2),
                "qty": round(qty, 6),
                "pnl": round(pnl, 2),
            })

        return order_id

    def get_position(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos["qty"] if pos else 0.0

    def get_bars(self, symbol: str, length: int) -> list[BarData]:
        return self.bars_cache.get(symbol, [])[-length:]

    def log(self, message: str):
        pass


async def run_backtest(db: AsyncSession, user_id: str, payload: dict) -> BacktestResult:
    result = BacktestResult(
        user_id=user_id,
        strategy_id=payload["strategy_id"],
        symbol=payload["symbol"],
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        timeframe=payload["timeframe"],
        initial_capital=payload["initial_capital"],
        params=payload.get("params"),
        status="running",
    )
    db.add(result)
    await db.flush()

    asyncio.create_task(_execute_backtest(result.id, user_id, payload))
    return result


async def _execute_backtest(result_id: str, user_id: str, payload: dict):
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            strategy = await db.get(Strategy, payload["strategy_id"])
            if not strategy:
                async with AsyncSessionLocal() as db2:
                    r = await db2.get(BacktestResult, result_id)
                    if r:
                        r.status = "failed"
                        r.error_message = "策略不存在"
                        await db2.commit()
                return
            strategy_code = strategy.code

        try:
            strategy_cls = _load_strategy_class(strategy_code)
        except Exception as e:
            async with AsyncSessionLocal() as db:
                r = await db.get(BacktestResult, result_id)
                if r:
                    r.status = "failed"
                    r.error_message = f"策略加载失败: {e}"
                    await db.commit()
            return

        provider = get_provider(payload["market"])
        klines = await provider.get_klines(
            symbol=payload["symbol"],
            timeframe=payload["timeframe"],
            start=str(payload["start_date"]),
            end=str(payload["end_date"]),
        )

        if not klines:
            async with AsyncSessionLocal() as db:
                r = await db.get(BacktestResult, result_id)
                if r:
                    r.status = "failed"
                    r.error_message = "无法获取历史数据"
                    await db.commit()
            return

        initial = float(payload["initial_capital"])
        commission_rate = float(payload.get("commission_rate") or 0.001)
        slippage = float(payload.get("slippage") or 0.001)

        ctx = BacktestContext(initial, commission_rate, slippage, payload["market"])
        strategy_instance = strategy_cls(payload.get("params") or {})
        strategy_instance.set_context(ctx)

        try:
            strategy_instance.on_init(ctx)
        except Exception as e:
            logger.warning("backtest.on_init_failed", error=str(e))

        symbol = payload["symbol"]
        for i, bar in enumerate(klines):
            close = float(bar["close"])
            bar_data = BarData(
                symbol=symbol,
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=close,
                volume=float(bar["volume"]),
                timestamp=bar["timestamp"],
            )

            if symbol not in ctx.bars_cache:
                ctx.bars_cache[symbol] = []
            ctx.bars_cache[symbol].append(bar_data)
            if len(ctx.bars_cache[symbol]) > 500:
                ctx.bars_cache[symbol] = ctx.bars_cache[symbol][-500:]

            try:
                ctx.current_price = close
                strategy_instance.on_bar(bar_data)
            except Exception as e:
                logger.warning("backtest.on_bar_error", error=str(e))

            equity = ctx.cash
            for sym, pos in ctx.positions.items():
                equity += pos["qty"] * close

            ctx.equity_curve.append({
                "timestamp": bar["timestamp"],
                "equity": round(equity, 2),
            })

        for sym, pos in list(ctx.positions.items()):
            if klines:
                last_close = float(klines[-1]["close"])
                ctx.cash += pos["qty"] * last_close
                del ctx.positions[sym]

        final_equity = ctx.cash
        total_return = (final_equity - initial) / initial
        trading_days = len(klines)
        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1 if trading_days > 0 else 0

        equity_values = [p["equity"] for p in ctx.equity_curve]
        returns = [(equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
                    for i in range(1, len(equity_values)) if equity_values[i - 1] > 0]

        sharpe_ratio = 0.0
        if returns:
            avg_ret = sum(returns) / len(returns)
            std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 0
            sharpe_ratio = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0

        peak = initial
        max_dd = 0.0
        drawdown_curve = []
        for i, eq in enumerate(equity_values):
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            drawdown_curve.append({
                "timestamp": ctx.equity_curve[i]["timestamp"],
                "drawdown": round(-dd * 100, 2),
            })

        completed_trades = [t for t in ctx.trades if t.get("exit_price") is not None]
        win_trades = [t for t in completed_trades if (t.get("pnl") or 0) > 0]
        win_rate = len(win_trades) / len(completed_trades) if completed_trades else 0

        total_profit = sum(t["pnl"] for t in win_trades) if win_trades else 0
        total_loss = abs(sum(t["pnl"] for t in [t for t in completed_trades if (t.get("pnl") or 0) < 0]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        monthly_returns = {}
        for i in range(1, len(equity_values)):
            ts = ctx.equity_curve[i]["timestamp"][:7]
            prev_eq = equity_values[i - 1]
            if prev_eq > 0:
                mr = (equity_values[i] - prev_eq) / prev_eq
                monthly_returns.setdefault(ts, []).append(mr)
        monthly_summary = {k: round(sum(v), 4) for k, v in monthly_returns.items()}

        down_returns = [r for r in returns if r < 0] if returns else []
        sortino = 0.0
        if down_returns:
            down_std = math.sqrt(sum(r ** 2 for r in down_returns) / len(down_returns))
            if down_std > 0 and returns:
                sortino = (sum(returns) / len(returns)) / down_std * math.sqrt(252)

        calmar = annual_return / max_dd if max_dd > 0 else 0

        total_holding_bars = 0
        for t in completed_trades:
            total_holding_bars += 1
        avg_holding = (total_holding_bars / len(completed_trades)) if completed_trades else 0

        async with AsyncSessionLocal() as db:
            r = await db.get(BacktestResult, result_id)
            if r:
                r.status = "completed"
                r.total_return = round(Decimal(str(total_return * 100)), 4)
                r.annual_return = round(Decimal(str(annual_return * 100)), 4)
                r.sharpe_ratio = round(Decimal(str(sharpe_ratio)), 4)
                r.sortino_ratio = round(Decimal(str(sortino)), 4)
                r.max_drawdown = round(Decimal(str(max_dd * 100)), 4)
                r.calmar_ratio = round(Decimal(str(calmar)), 4)
                r.win_rate = round(Decimal(str(win_rate * 100)), 4)
                r.profit_factor = round(Decimal(str(profit_factor)), 4)
                r.trade_count = len(completed_trades)
                r.avg_holding_period = round(Decimal(str(avg_holding)), 2)
                r.equity_curve = {"data": ctx.equity_curve}
                r.drawdown_curve = {"data": drawdown_curve}
                r.trades = {"data": ctx.trades}
                r.monthly_returns = monthly_summary
                await db.commit()

    except Exception as e:
        logger.exception("backtest.execution_failed", result_id=result_id, error=str(e))
        try:
            async with AsyncSessionLocal() as db:
                r = await db.get(BacktestResult, result_id)
                if r:
                    r.status = "failed"
                    r.error_message = str(e)[:1000]
                    await db.commit()
        except Exception:
            pass


async def list_backtest_results(
    db: AsyncSession, user_id: str, strategy_id: str | None = None
) -> list[BacktestResult]:
    query = select(BacktestResult).where(BacktestResult.user_id == user_id)
    if strategy_id:
        query = query.where(BacktestResult.strategy_id == strategy_id)
    query = query.order_by(BacktestResult.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_backtest_result(db: AsyncSession, user_id: str, result_id: str) -> BacktestResult | None:
    result = await db.get(BacktestResult, result_id)
    if result and result.user_id != user_id:
        return None
    return result


async def delete_backtest_result(db: AsyncSession, user_id: str, result_id: str) -> bool:
    result = await db.get(BacktestResult, result_id)
    if not result or result.user_id != user_id:
        return False
    await db.delete(result)
    await db.flush()
    return True
