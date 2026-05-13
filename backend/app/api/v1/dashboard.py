from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.dashboard import DashboardOverview, EquityCurvePoint, StrategyRankItem
from app.services.account_service import get_account_info
from app.models.market_data import BacktestResult

router = APIRouter()


@router.get("/overview", response_model=ResponseBase[dict])
async def get_overview(user: CurrentUser, db: DBSession):
    info = await get_account_info(db, user.id)
    return ResponseBase(data=info)


@router.get("/equity-curve", response_model=ResponseBase[list[EquityCurvePoint]])
async def get_equity_curve(
    user: CurrentUser,
    db: DBSession,
    range: str = Query("1M", pattern=r"^(1D|1W|1M|3M|1Y|ALL)$"),
):
    from app.services.market_service import MockDataProvider
    provider = MockDataProvider()
    klines = await provider.get_klines("BTCUSDT", "1d", limit=90)

    points = []
    for i, k in enumerate(klines):
        equity = 1000000 * (1 + i * 0.001)
        points.append(EquityCurvePoint(
            date=k["timestamp"][:10],
            equity=round(equity, 2),
            benchmark=1000000,
        ))
    return ResponseBase(data=points)


@router.get("/strategy-ranking", response_model=ResponseBase[list[StrategyRankItem]])
async def get_strategy_ranking(user: CurrentUser, db: DBSession):
    from app.models.strategy import Strategy
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == user.id, Strategy.status == "running")
    )
    strategies = result.scalars().all()

    backtest_result = await db.execute(
        select(BacktestResult).where(BacktestResult.user_id == user.id)
        .order_by(BacktestResult.created_at.desc())
    )
    backtests = {str(bt.strategy_id): bt for bt in backtest_result.scalars().all()}

    items = []
    for s in strategies:
        bt = backtests.get(str(s.id))
        items.append(StrategyRankItem(
            strategy_id=s.id,
            name=s.name,
            total_return=float(bt.total_return) if bt and bt.total_return else 0,
            sharpe_ratio=float(bt.sharpe_ratio) if bt and bt.sharpe_ratio else 0,
            max_drawdown=float(bt.max_drawdown) if bt and bt.max_drawdown else 0,
            trade_count=bt.trade_count if bt else 0,
            status=s.status,
        ))
    return ResponseBase(data=items)
