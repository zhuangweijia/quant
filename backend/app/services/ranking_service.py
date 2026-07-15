"""Ranking service — generates daily stock rankings from model predictions."""

from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction

logger = structlog.get_logger()

# Label thresholds (percentile of score distribution)
TOP_STRONG = 0.10  # Top 10% → 强推
TOP_WATCH = 0.40  # Top 10%-40% → 关注
BOTTOM_AVOID = 0.10  # Bottom 10% → 回避
# Middle 40%-90% → 观望

LABELS = {
    "strong": "强推",
    "watch": "关注",
    "hold": "观望",
    "avoid": "回避",
}


async def generate_daily_ranking(db: AsyncSession, trade_date: date) -> dict:
    """Generate rankings for a given trade date.

    Reads all predictions for trade_date, sorts by score descending,
    assigns rank numbers and labels, computes rank change vs previous day.

    Returns summary dict: {date, total, strong, watch, hold, avoid}
    """
    result = await db.execute(
        select(Prediction)
        .where(Prediction.trade_date == trade_date)
        .order_by(Prediction.score.desc())
    )
    predictions = result.scalars().all()

    if not predictions:
        logger.warning("ranking.no_predictions", trade_date=str(trade_date))
        return {"date": str(trade_date), "total": 0}

    total = len(predictions)
    strong_cutoff = max(1, int(total * TOP_STRONG))
    watch_cutoff = max(1, int(total * TOP_WATCH))
    avoid_cutoff = total - max(1, int(total * BOTTOM_AVOID))

    # Get previous trading day's ranks for rank_change calculation
    prev_ranks = await _get_previous_ranks(db, trade_date)

    for i, pred in enumerate(predictions):
        pred.rank = i + 1

        if i < strong_cutoff:
            pred.label = LABELS["strong"]
        elif i < watch_cutoff:
            pred.label = LABELS["watch"]
        elif i >= avoid_cutoff:
            pred.label = LABELS["avoid"]
        else:
            pred.label = LABELS["hold"]

        # Rank change: positive = moved up
        prev_rank = prev_ranks.get(pred.symbol)
        current_rank = i + 1
        if prev_rank is not None:
            pred.rank_change = prev_rank - current_rank  # positive = improved
        else:
            pred.rank_change = None  # NEW entry

    await db.flush()

    summary = {
        "date": str(trade_date),
        "total": total,
        "strong": strong_cutoff,
        "watch": watch_cutoff - strong_cutoff,
        "hold": avoid_cutoff - watch_cutoff,
        "avoid": total - avoid_cutoff,
    }

    logger.info("ranking.generated", **summary)
    return summary


async def _get_previous_ranks(db: AsyncSession, trade_date: date) -> dict[str, int]:
    """Get the most recent previous trading day's rank for each symbol.

    Returns dict: {symbol: rank}
    """
    # Find the most recent date before trade_date that has predictions
    result = await db.execute(
        select(Prediction.trade_date)
        .where(Prediction.trade_date < trade_date)
        .distinct()
        .order_by(Prediction.trade_date.desc())
        .limit(1)
    )
    prev_date = result.scalar_one_or_none()

    if prev_date is None:
        return {}

    result = await db.execute(
        select(Prediction.symbol, Prediction.rank).where(Prediction.trade_date == prev_date)
    )
    return {symbol: rank for symbol, rank in result.all() if rank is not None}
