"""Ranking API — daily stock rankings."""

from datetime import date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.deps import DBSession
from app.schemas.common import ResponseBase
from app.schemas.ranking import RankingItem, RankingResponse
from app.models.prediction import Prediction
from app.models.stock import Stock

router = APIRouter()


@router.get("", response_model=ResponseBase[RankingResponse])
async def get_rankings(
    db: DBSession,
    date: str = Query("today", description="日期 YYYY-MM-DD 或 'today'"),
    label: str | None = Query(None, description="筛选标签: 强推/关注/观望/回避"),
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=300),
):
    target_date = _resolve_date(date)

    query = select(Prediction, Stock).outerjoin(
        Stock, Prediction.symbol == Stock.symbol
    ).where(Prediction.trade_date == target_date)

    if label:
        query = query.where(Prediction.label == label)

    # Get total count
    count_query = select(func.count()).select_from(Prediction).where(
        Prediction.trade_date == target_date
    )
    if label:
        count_query = count_query.where(Prediction.label == label)
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Prediction.rank.asc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)

    items = []
    for pred, stock in result.all():
        items.append(RankingItem(
            rank=pred.rank or 0,
            symbol=pred.symbol,
            name=stock.name if stock else None,
            score=pred.score,
            label=pred.label,
            rank_change=pred.rank_change,
            confidence=pred.confidence,
        ))

    return ResponseBase(data=RankingResponse(
        date=str(target_date),
        total=total,
        items=items,
    ))


def _resolve_date(s: str) -> date:
    if s == "today":
        return date.today()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return date.today()
