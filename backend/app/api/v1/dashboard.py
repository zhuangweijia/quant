from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.dashboard import DashboardOverview, EquityCurvePoint, StrategyRankItem

router = APIRouter()


@router.get("/overview", response_model=ResponseBase[DashboardOverview])
async def get_overview(user: CurrentUser, db: DBSession):
    return ResponseBase(
        data=DashboardOverview(
            total_equity=0,
            cash=0,
            position_value=0,
            daily_pnl=0,
            daily_pnl_pct=0,
            total_pnl=0,
            total_pnl_pct=0,
            running_strategies=0,
            total_strategies=0,
            today_trades=0,
            unread_alerts=0,
        ),
        message="Dashboard 模块待实现",
    )


@router.get("/equity-curve", response_model=ResponseBase[list[EquityCurvePoint]])
async def get_equity_curve(
    user: CurrentUser,
    db: DBSession,
    range: str = Query("1M", pattern=r"^(1D|1W|1M|3M|1Y|ALL)$"),
):
    return ResponseBase(data=[], message="Dashboard 模块待实现")


@router.get("/strategy-ranking", response_model=ResponseBase[list[StrategyRankItem]])
async def get_strategy_ranking(user: CurrentUser, db: DBSession):
    return ResponseBase(data=[], message="Dashboard 模块待实现")
