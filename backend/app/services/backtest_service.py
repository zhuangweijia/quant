import asyncio
import random
import math
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import BacktestResult
from app.models.strategy import Strategy
from app.services.market_service import MockDataProvider
import structlog

logger = structlog.get_logger()


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
        provider = MockDataProvider()
        klines = await provider.get_klines(
            symbol=payload["symbol"],
            timeframe=payload["timeframe"],
            start=str(payload["start_date"]),
            end=str(payload["end_date"]),
        )

        if not klines:
            async with AsyncSessionLocal() as db:
                result = await db.get(BacktestResult, result_id)
                if result:
                    result.status = "failed"
                    result.error_message = "无法获取历史数据"
                    await db.commit()
            return

        initial = float(payload["initial_capital"])
        commission_rate = float(payload.get("commission_rate") or 0.001)
        slippage = float(payload.get("slippage") or 0.001)

        cash = initial
        position_qty = 0.0
        position_avg = 0.0
        equity_curve = []
        trades = []
        total_bars = len(klines)

        short_ma_period = 10
        long_ma_period = 30
        closes = []

        for i, bar in enumerate(klines):
            close = float(bar["close"])
            high = float(bar["high"])
            low = float(bar["low"])
            closes.append(close)

            if len(closes) < long_ma_period:
                equity = cash + position_qty * close
                equity_curve.append({"timestamp": bar["timestamp"], "equity": round(equity, 2)})
                continue

            short_ma = sum(closes[-short_ma_period:]) / short_ma_period
            long_ma = sum(closes[-long_ma_period:]) / long_ma_period

            if short_ma > long_ma and position_qty == 0:
                buy_price = close * (1 + slippage)
                qty = (cash * 0.95) / buy_price
                if qty > 0:
                    commission = buy_price * qty * commission_rate
                    cash -= (buy_price * qty + commission)
                    position_qty = qty
                    position_avg = buy_price
                    trades.append({
                        "entry_time": bar["timestamp"],
                        "exit_time": None,
                        "symbol": payload["symbol"],
                        "side": "buy",
                        "entry_price": round(buy_price, 2),
                        "exit_price": None,
                        "qty": round(qty, 6),
                        "pnl": None,
                    })

            elif short_ma < long_ma and position_qty > 0:
                sell_price = close * (1 - slippage)
                commission = sell_price * position_qty * commission_rate
                proceeds = sell_price * position_qty - commission
                pnl = proceeds - (position_avg * position_qty)
                cash += proceeds

                if trades and trades[-1]["exit_time"] is None:
                    trades[-1]["exit_time"] = bar["timestamp"]
                    trades[-1]["exit_price"] = round(sell_price, 2)
                    trades[-1]["pnl"] = round(pnl, 2)

                position_qty = 0
                position_avg = 0

            equity = cash + position_qty * close
            equity_curve.append({"timestamp": bar["timestamp"], "equity": round(equity, 2)})

        if position_qty > 0 and klines:
            last_close = float(klines[-1]["close"])
            cash += position_qty * last_close
            if trades and trades[-1]["exit_time"] is None:
                trades[-1]["exit_time"] = klines[-1]["timestamp"]
                trades[-1]["exit_price"] = round(last_close, 2)
                trades[-1]["pnl"] = round(last_close * position_qty - position_avg * position_qty, 2)
            position_qty = 0

        final_equity = cash
        total_return = (final_equity - initial) / initial
        trading_days = len(klines)
        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1 if trading_days > 0 else 0

        equity_values = [p["equity"] for p in equity_curve]
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
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            drawdown_curve.append({"timestamp": equity_curve[len(drawdown_curve)]["timestamp"], "drawdown": round(-dd * 100, 2)})

        completed_trades = [t for t in trades if t["exit_time"] is not None]
        win_trades = [t for t in completed_trades if (t.get("pnl") or 0) > 0]
        win_rate = len(win_trades) / len(completed_trades) if completed_trades else 0

        avg_win = sum(t["pnl"] for t in win_trades) / len(win_trades) if win_trades else 0
        loss_trades = [t for t in completed_trades if (t.get("pnl") or 0) < 0]
        avg_loss = abs(sum(t["pnl"] for t in loss_trades) / len(loss_trades)) if loss_trades else 0
        profit_factor = (avg_win * len(win_trades)) / (avg_loss * len(loss_trades)) if loss_trades and avg_loss > 0 else 0

        total_profit = sum(t["pnl"] for t in win_trades) if win_trades else 0
        total_loss = abs(sum(t["pnl"] for t in loss_trades)) if loss_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        monthly_returns = {}
        for i in range(1, len(equity_values)):
            ts = equity_curve[i]["timestamp"][:7]
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

        async with AsyncSessionLocal() as db:
            result = await db.get(BacktestResult, result_id)
            if result:
                result.status = "completed"
                result.total_return = round(Decimal(str(total_return * 100)), 4)
                result.annual_return = round(Decimal(str(annual_return * 100)), 4)
                result.sharpe_ratio = round(Decimal(str(sharpe_ratio)), 4)
                result.sortino_ratio = round(Decimal(str(sortino)), 4)
                result.max_drawdown = round(Decimal(str(max_dd * 100)), 4)
                result.calmar_ratio = round(Decimal(str(calmar)), 4)
                result.win_rate = round(Decimal(str(win_rate * 100)), 4)
                result.profit_factor = round(Decimal(str(profit_factor)), 4)
                result.trade_count = len(completed_trades)
                result.avg_holding_period = Decimal("0")
                result.equity_curve = {"data": equity_curve}
                result.drawdown_curve = {"data": drawdown_curve}
                result.trades = {"data": trades}
                result.monthly_returns = monthly_summary
                await db.commit()

    except Exception as e:
        logger.exception("backtest.execution_failed", result_id=result_id, error=str(e))
        try:
            async with AsyncSessionLocal() as db:
                result = await db.get(BacktestResult, result_id)
                if result:
                    result.status = "failed"
                    result.error_message = str(e)[:1000]
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
