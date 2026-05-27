from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.models.strategy import Strategy
from app.schemas.common import ResponseBase, PageResponse
from app.schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyListItem,
    StrategyDetail,
)
from app.models.strategy_version import StrategyVersion

router = APIRouter()


@router.get("", response_model=ResponseBase[PageResponse[StrategyListItem]])
async def list_strategies(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    strategy_status: str | None = Query(None, alias="status"),
    market: str | None = Query(None),
    keyword: str | None = Query(None),
):
    query = select(Strategy).where(
        Strategy.user_id == user.id,
        Strategy.deleted_at.is_(None),
    )
    count_query = select(func.count(Strategy.id)).where(
        Strategy.user_id == user.id,
        Strategy.deleted_at.is_(None),
    )

    if strategy_status:
        query = query.where(Strategy.status == strategy_status)
        count_query = count_query.where(Strategy.status == strategy_status)
    if market:
        query = query.where(Strategy.market == market)
        count_query = count_query.where(Strategy.market == market)
    if keyword:
        query = query.where(Strategy.name.ilike(f"%{keyword}%"))
        count_query = count_query.where(Strategy.name.ilike(f"%{keyword}%"))

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    query = query.order_by(Strategy.updated_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    strategies = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=PageResponse(
            items=[StrategyListItem.model_validate(s) for s in strategies],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.post("", response_model=ResponseBase[StrategyDetail], status_code=201)
async def create_strategy(
    user: CurrentUser,
    db: DBSession,
    payload: StrategyCreate,
):
    count = await db.scalar(
        select(func.count(Strategy.id)).where(
            Strategy.user_id == user.id,
            Strategy.deleted_at.is_(None),
        )
    )
    if count and count >= 50:
        raise HTTPException(status_code=400, detail="策略数量已达上限 (50)")

    strategy = Strategy(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        code=payload.code,
        params=payload.params,
        market=payload.market,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        status="draft",
    )
    db.add(strategy)
    await db.flush()
    return ResponseBase(data=StrategyDetail.model_validate(strategy))


@router.get("/{strategy_id}", response_model=ResponseBase[StrategyDetail])
async def get_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id or strategy.deleted_at:
        raise HTTPException(status_code=404, detail="策略不存在")
    return ResponseBase(data=StrategyDetail.model_validate(strategy))


@router.put("/{strategy_id}", response_model=ResponseBase[StrategyDetail])
async def update_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
    payload: StrategyUpdate,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id or strategy.deleted_at:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.status == "running":
        raise HTTPException(status_code=400, detail="运行中的策略不能编辑，请先停止")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(strategy, key, value)
    strategy.status = "draft"

    max_ver = await db.scalar(
        select(func.max(StrategyVersion.version)).where(
            StrategyVersion.strategy_id == strategy.id,
        )
    )
    new_ver = (max_ver or 0) + 1
    snapshot = StrategyVersion(
        strategy_id=strategy.id,
        version=new_ver,
        code=strategy.code,
        params=strategy.params,
    )
    db.add(snapshot)
    await db.flush()
    return ResponseBase(data=StrategyDetail.model_validate(strategy))


@router.delete("/{strategy_id}", response_model=ResponseBase[None])
async def delete_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id or strategy.deleted_at:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.status == "running":
        raise HTTPException(status_code=400, detail="运行中的策略不能删除，请先停止")

    from datetime import datetime, timezone
    strategy.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ResponseBase()


@router.post("/{strategy_id}/start", response_model=ResponseBase[None])
async def start_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id or strategy.deleted_at:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.status == "running":
        raise HTTPException(status_code=400, detail="策略已在运行中")

    running_count = await db.scalar(
        select(func.count(Strategy.id)).where(
            Strategy.user_id == user.id,
            Strategy.status == "running",
        )
    )
    if running_count and running_count >= 10:
        raise HTTPException(status_code=400, detail="同时运行策略数已达上限 (10)")

    from app.services.strategy_engine import strategy_engine
    try:
        default_symbol = strategy.symbol or (
            "BTCUSDT" if strategy.market == "crypto" else
            "AAPL" if strategy.market == "us_stock" else
            "000001"
        )
        tf = strategy.timeframe or "1d"
        await strategy_engine.start_strategy(
            strategy_id=str(strategy.id),
            user_id=str(user.id),
            code=strategy.code,
            params=strategy.params or {},
            market=strategy.market,
            timeframe=tf,
            symbol=default_symbol,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"策略启动失败: {e}")

    strategy.status = "running"
    await db.flush()
    return ResponseBase()


@router.post("/{strategy_id}/stop", response_model=ResponseBase[None])
async def stop_strategy(
    user: CurrentUser,
    db: DBSession,
    strategy_id: UUID,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id or strategy.deleted_at:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.status != "running":
        raise HTTPException(status_code=400, detail="策略未在运行")

    from app.services.strategy_engine import strategy_engine
    await strategy_engine.stop_strategy(str(strategy.id))

    strategy.status = "stopped"
    await db.flush()
    return ResponseBase()
