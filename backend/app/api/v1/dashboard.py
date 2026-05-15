from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.dashboard import DashboardOverview, EquityCurvePoint, StrategyRankItem
from app.services.account_service import get_account_info
from app.models.market_data import BacktestResult
from app.models.equity_snapshot import EquitySnapshot

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
    from datetime import timedelta, datetime, timezone
    range_days = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365, "ALL": 9999}
    days = range_days.get(range, 30)

    query = select(EquitySnapshot).where(
        EquitySnapshot.user_id == user.id,
    ).order_by(EquitySnapshot.date.asc())

    if days < 9999:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        query = query.where(EquitySnapshot.date >= cutoff)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        from app.services.account_service import get_or_create_account
        account = await get_or_create_account(db, user.id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return ResponseBase(data=[EquityCurvePoint(
            date=today,
            equity=float(account.cash),
            benchmark=float(account.initial_capital),
        )])

    points = []
    initial = float(snapshots[0].total_equity) if snapshots else 1000000
    for snap in snapshots:
        points.append(EquityCurvePoint(
            date=snap.date,
            equity=float(snap.total_equity),
            benchmark=initial,
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
