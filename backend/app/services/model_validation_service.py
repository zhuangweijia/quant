"""Model validation service — quintile backtest for ranking-based selection."""

from datetime import date, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction
from app.models.daily_bar import DailyBar

logger = structlog.get_logger()


async def run_quintile_backtest(
    db: AsyncSession,
    model_version: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Run quintile group backtest on historical predictions/rankings.

    Splits stocks into 5 groups by score each day, computes equal-weight
    daily returns per group, and derives performance metrics.
    """
    if not start_date:
        start_date = date.today().replace(year=date.today().year - 1)
    if not end_date:
        end_date = date.today()

    # Load predictions
    query = select(Prediction).where(
        Prediction.trade_date >= start_date,
        Prediction.trade_date <= end_date,
    )
    if model_version:
        query = query.where(Prediction.model_version == model_version)

    result = await db.execute(query.order_by(Prediction.trade_date, Prediction.score.desc()))
    all_preds = result.scalars().all()

    if not all_preds:
        return {
            "model_version": model_version or "all",
            "start_date": start_date,
            "end_date": end_date,
            "group_returns": {},
            "ic_series": [],
            "metrics": {"error": "no predictions found"},
        }

    # Group predictions by date
    preds_by_date: dict[date, list[Prediction]] = {}
    for p in all_preds:
        preds_by_date.setdefault(p.trade_date, []).append(p)

    # For each date, assign quintile groups
    daily_group_returns: dict[str, list[dict]] = {f"Q{i+1}": [] for i in range(5)}
    ic_series = []
    sorted_dates = sorted(preds_by_date.keys())

    for trade_date in sorted_dates:
        preds = preds_by_date[trade_date]
        preds_sorted = sorted(preds, key=lambda x: x.score, reverse=True)
        n = len(preds_sorted)
        if n < 5:
            continue

        group_size = n // 5
        groups = []
        for i in range(5):
            start_idx = i * group_size
            end_idx = start_idx + group_size if i < 4 else n
            groups.append(preds_sorted[start_idx:end_idx])

        # Compute next-day returns for each group
        group_returns = []
        for group in groups:
            rets = await _compute_group_return(db, [p.symbol for p in group], trade_date)
            group_returns.append(rets)
            daily_group_returns[f"Q{i+1}"].append({
                "date": str(trade_date),
                "return": rets,
            })

        # IC: Spearman correlation between score and forward return
        symbols = [p.symbol for p in preds_sorted]
        scores = [float(p.score) for p in preds_sorted]
        fwd_returns = await _compute_forward_returns(db, symbols, trade_date)

        if len(scores) > 5 and len(fwd_returns) == len(scores):
            try:
                from scipy.stats import spearmanr
                valid = [(s, r) for s, r in zip(scores, fwd_returns) if r is not None]
                if len(valid) > 5:
                    s_vals = [v[0] for v in valid]
                    r_vals = [v[1] for v in valid]
                    ic, _ = spearmanr(s_vals, r_vals)
                    ic_series.append({"date": str(trade_date), "ic": float(ic)})
            except Exception:
                pass

    # Compute metrics for each group
    metrics = {}
    for q_name, daily_rets in daily_group_returns.items():
        if not daily_rets:
            continue
        rets = [d["return"] for d in daily_rets if d["return"] is not None]
        if not rets:
            continue

        cumulative = 1.0
        for r in rets:
            cumulative *= (1 + r)

        metrics[q_name] = {
            "total_return": cumulative - 1,
            "annual_return": cumulative ** (252 / len(rets)) - 1 if len(rets) > 0 else 0,
            "sharpe": _sharpe(rets),
            "max_drawdown": _max_drawdown(rets),
            "n_days": len(rets),
        }

    # Top-Bottom spread
    if "Q1" in metrics and "Q5" in metrics:
        metrics["long_short"] = {
            "annual_return": metrics["Q1"]["annual_return"] - metrics["Q5"]["annual_return"],
        }

    # IC stats
    ic_values = [d["ic"] for d in ic_series if d["ic"] is not None]
    if ic_values:
        metrics["ic"] = {
            "mean": sum(ic_values) / len(ic_values),
            "win_rate": sum(1 for v in ic_values if v > 0) / len(ic_values),
            "n_days": len(ic_values),
        }

    return {
        "model_version": model_version or "all",
        "start_date": start_date,
        "end_date": end_date,
        "group_returns": daily_group_returns,
        "ic_series": ic_series,
        "metrics": metrics,
    }


async def _compute_group_return(
    db: AsyncSession, symbols: list[str], trade_date: date
) -> float | None:
    """Compute equal-weight next-day return for a group of symbols."""
    if not symbols:
        return None

    next_day = trade_date + timedelta(days=1)
    # Look for returns over 5 trading days
    end_day = trade_date + timedelta(days=10)

    result = await db.execute(
        select(DailyBar.symbol, DailyBar.close, DailyBar.trade_date).where(
            DailyBar.symbol.in_(symbols),
            DailyBar.trade_date >= trade_date,
            DailyBar.trade_date <= end_day,
        ).order_by(DailyBar.symbol, DailyBar.trade_date)
    )
    rows = result.all()

    if not rows:
        return None

    # Compute per-symbol return
    by_symbol: dict[str, list] = {}
    for sym, close, td in rows:
        by_symbol.setdefault(sym, []).append((td, float(close)))

    returns = []
    for sym, prices in by_symbol.items():
        if len(prices) >= 2:
            ret = (prices[-1][1] / prices[0][1]) - 1
            returns.append(ret)

    return sum(returns) / len(returns) if returns else None


async def _compute_forward_returns(
    db: AsyncSession, symbols: list[str], trade_date: date
) -> list[float | None]:
    """Compute forward 5-day return for each symbol."""
    end_day = trade_date + timedelta(days=10)

    result = await db.execute(
        select(DailyBar.symbol, DailyBar.close, DailyBar.trade_date).where(
            DailyBar.symbol.in_(symbols),
            DailyBar.trade_date >= trade_date,
            DailyBar.trade_date <= end_day,
        ).order_by(DailyBar.symbol, DailyBar.trade_date)
    )
    rows = result.all()

    by_symbol: dict[str, list] = {}
    for sym, close, td in rows:
        by_symbol.setdefault(sym, []).append((td, float(close)))

    fwd_returns = []
    for sym in symbols:
        prices = by_symbol.get(sym, [])
        if len(prices) >= 2:
            fwd_returns.append((prices[-1][1] / prices[0][1]) - 1)
        else:
            fwd_returns.append(None)

    return fwd_returns


def _sharpe(returns: list[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    return (mean_r / std) * (periods_per_year ** 0.5)


def _max_drawdown(returns: list[float]) -> float:
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cumulative *= (1 + r)
        if cumulative > peak:
            peak = cumulative
        dd = (cumulative - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd
