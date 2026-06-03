from fastapi import APIRouter, Query
from sqlalchemy import select, func, text

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.dashboard import DashboardOverview, EquityCurvePoint, StrategyRankItem
from app.services.account_service import get_account_info, get_or_create_account, calc_position_values
from app.models.market_data import BacktestResult
from app.models.equity_snapshot import EquitySnapshot
from app.models.strategy import Strategy

router = APIRouter()


@router.get("/overview", response_model=ResponseBase[DashboardOverview])
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

    account = await get_or_create_account(db, user.id)
    benchmark = float(account.initial_capital)
    range_days = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365, "ALL": 9999}
    days = range_days.get(range, 30)

    query = select(EquitySnapshot).where(
        EquitySnapshot.user_id == user.id,
    ).order_by(EquitySnapshot.timestamp.asc())

    if days < 9999:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(EquitySnapshot.timestamp >= cutoff)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        now = datetime.now(timezone.utc)
        return ResponseBase(data=[EquityCurvePoint(
            date=now.strftime("%Y-%m-%d %H:%M"),
            equity=float(account.cash),
            benchmark=benchmark,
        )])

    if range in ("1D", "1W"):
        points = [EquityCurvePoint(
            date=s.timestamp.strftime("%Y-%m-%d %H:%M"),
            equity=float(s.total_equity),
            benchmark=benchmark,
        ) for s in snapshots]
    else:
        daily: dict[str, EquitySnapshot] = {}
        for s in snapshots:
            day_key = s.timestamp.strftime("%Y-%m-%d")
            daily[day_key] = s
        points = [EquityCurvePoint(
            date=day,
            equity=float(s.total_equity),
            benchmark=benchmark,
        ) for day, s in sorted(daily.items())]

    return ResponseBase(data=points)


@router.get("/strategy-ranking", response_model=ResponseBase[list[StrategyRankItem]])
async def get_strategy_ranking(user: CurrentUser, db: DBSession):
    backtest_result = await db.execute(
        select(BacktestResult).where(BacktestResult.user_id == user.id)
        .order_by(BacktestResult.created_at.desc())
    )
    backtests = {str(bt.strategy_id): bt for bt in backtest_result.scalars().all()}

    if not backtests:
        return ResponseBase(data=[])

    strategy_ids = list(backtests.keys())
    result = await db.execute(
        select(Strategy).where(
            Strategy.user_id == user.id,
            Strategy.id.in_([text(f"'{sid}'") for sid in strategy_ids[:10]]),
        )
    )
    strategies = {str(s.id): s for s in result.scalars().all()}

    items = []
    for sid, bt in backtests.items():
        s = strategies.get(sid)
        items.append(StrategyRankItem(
            strategy_id=bt.strategy_id,
            name=s.name if s else str(bt.strategy_id),
            total_return=float(bt.total_return) if bt.total_return else 0,
            sharpe_ratio=float(bt.sharpe_ratio) if bt.sharpe_ratio else 0,
            max_drawdown=float(bt.max_drawdown) if bt.max_drawdown else 0,
            trade_count=bt.trade_count if bt.trade_count else 0,
            status=s.status if s else "unknown",
        ))

    items.sort(key=lambda x: x.total_return, reverse=True)
    return ResponseBase(data=items[:10])
