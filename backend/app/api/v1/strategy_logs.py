from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.models.strategy_log import StrategyLog
from app.schemas.common import ResponseBase, PageResponse
from pydantic import BaseModel

router = APIRouter()


class StrategyLogItem(BaseModel):
    id: str
    strategy_id: str
    level: str
    message: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/{strategy_id}/logs", response_model=ResponseBase[PageResponse[StrategyLogItem]])
async def get_strategy_logs(
    user: CurrentUser,
    db: DBSession,
    strategy_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    from app.models.strategy import Strategy
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id:
        raise HTTPException(status_code=404, detail="策略不存在")

    count = await db.scalar(
        select(func.count(StrategyLog.id)).where(
            StrategyLog.strategy_id == strategy_id,
            StrategyLog.user_id == user.id,
        )
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(StrategyLog)
        .where(StrategyLog.strategy_id == strategy_id, StrategyLog.user_id == user.id)
        .order_by(StrategyLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    total_pages = (count + page_size - 1) // page_size if count else 0
    return ResponseBase(
        data=PageResponse(
            items=[StrategyLogItem.model_validate(l) for l in logs],
            total=count or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )
