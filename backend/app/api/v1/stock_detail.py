"""Stock detail API — individual stock drill-down."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DBSession
from app.models.daily_bar import DailyBar
from app.models.prediction import Prediction
from app.models.stock import Stock
from app.models.stock_factor import StockFactor
from app.schemas.common import ResponseBase
from app.schemas.ranking import ScoreHistoryItem, ScoreHistoryResponse, StockDetailResponse

router = APIRouter()


@router.get("/{symbol}/detail", response_model=ResponseBase[StockDetailResponse])
async def get_stock_detail(symbol: str, db: DBSession):
    stock = await db.execute(select(Stock).where(Stock.symbol == symbol))
    stock = stock.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")

    # Latest prediction
    pred = await db.execute(
        select(Prediction)
        .where(Prediction.symbol == symbol)
        .order_by(Prediction.trade_date.desc())
        .limit(1)
    )
    pred = pred.scalar_one_or_none()

    # Latest factors
    factors = await db.execute(
        select(StockFactor)
        .where(StockFactor.symbol == symbol)
        .order_by(StockFactor.trade_date.desc())
        .limit(1)
    )
    factors = factors.scalar_one_or_none()

    # Last 60 days K-lines
    klines_result = await db.execute(
        select(DailyBar)
        .where(DailyBar.symbol == symbol)
        .order_by(DailyBar.trade_date.desc())
        .limit(60)
    )
    klines = []
    for bar in reversed(klines_result.scalars().all()):
        klines.append(
            {
                "date": str(bar.trade_date),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
            }
        )

    # Northbound from Redis
    northbound = None
    try:
        import redis.asyncio as aioredis

        from app.config import get_settings

        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        nb_pct = await r.get(f"northbound:{symbol}")
        if nb_pct:
            northbound = {"holding_pct": float(nb_pct)}
        await r.aclose()
    except Exception:
        pass

    # Fundamentals from Redis
    fundamentals = None
    try:
        import json

        import redis.asyncio as aioredis

        from app.config import get_settings

        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        raw = await r.get(f"fundamental:{symbol}")
        if raw:
            fundamentals = json.loads(raw.replace("'", '"'))
        await r.aclose()
    except Exception:
        pass

    return ResponseBase(
        data=StockDetailResponse(
            symbol=symbol,
            name=stock.name,
            industry=stock.industry,
            score=pred.score if pred else None,
            rank=pred.rank if pred else None,
            label=pred.label if pred else None,
            confidence=pred.confidence if pred else "normal",
            explanation=pred.explanation if pred else None,
            fundamentals=fundamentals,
            klines=klines,
            northbound=northbound,
        )
    )


@router.get("/{symbol}/score-history", response_model=ResponseBase[ScoreHistoryResponse])
async def get_score_history(
    symbol: str,
    db: DBSession,
    days: int = Query(30, ge=1, le=365),
):
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(Prediction)
        .where(Prediction.symbol == symbol, Prediction.trade_date >= cutoff)
        .order_by(Prediction.trade_date.asc())
    )

    history = [
        ScoreHistoryItem(
            date=str(p.trade_date),
            score=p.score,
            rank=p.rank,
            label=p.label,
        )
        for p in result.scalars().all()
    ]

    return ResponseBase(data=ScoreHistoryResponse(symbol=symbol, history=history))
