from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase, PageResponse
from app.schemas.backtest import BacktestRunRequest, BacktestResultListItem, BacktestResultDetail
from app.services.backtest_service import (
    run_backtest, list_backtest_results, get_backtest_result, delete_backtest_result,
)

router = APIRouter()


@router.post("/run", response_model=ResponseBase[BacktestResultListItem], status_code=201)
async def api_run_backtest(user: CurrentUser, db: DBSession, payload: BacktestRunRequest):
    payload_dict = {
        "strategy_id": str(payload.strategy_id),
        "symbol": payload.symbol,
        "market": payload.market,
        "timeframe": payload.timeframe,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "initial_capital": payload.initial_capital,
        "commission_rate": payload.commission_rate,
        "slippage": payload.slippage,
        "params": payload.params,
    }
    result = await run_backtest(db, user.id, payload_dict)
    return ResponseBase(data=BacktestResultListItem.model_validate(result))


@router.get("/results", response_model=ResponseBase[PageResponse[BacktestResultListItem]])
async def api_list_results(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    strategy_id: str | None = Query(None),
):
    from app.models.market_data import BacktestResult
    count_query = select(func.count(BacktestResult.id)).where(BacktestResult.user_id == user.id)
    data_query = select(BacktestResult).where(BacktestResult.user_id == user.id)

    if strategy_id:
        sid = UUID(strategy_id)
        count_query = count_query.where(BacktestResult.strategy_id == sid)
        data_query = data_query.where(BacktestResult.strategy_id == sid)

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    data_query = data_query.order_by(BacktestResult.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(data_query)
    results = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=PageResponse(
            items=[BacktestResultListItem.model_validate(r) for r in results],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/results/{result_id}", response_model=ResponseBase[BacktestResultDetail])
async def api_get_result(user: CurrentUser, db: DBSession, result_id: UUID):
    result = await get_backtest_result(db, str(user.id), str(result_id))
    if not result:
        raise HTTPException(status_code=404, detail="回测结果不存在")
    return ResponseBase(data=BacktestResultDetail.model_validate(result))


@router.delete("/results/{result_id}", response_model=ResponseBase[None])
async def api_delete_result(user: CurrentUser, db: DBSession, result_id: UUID):
    deleted = await delete_backtest_result(db, str(user.id), str(result_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="回测结果不存在")
    return ResponseBase()
