from fastapi import APIRouter

from app.api.v1 import auth, market, strategy, backtest, trade, risk, dashboard, settings
from app.api.v1 import strategy_logs, watchlist

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(market.router, prefix="/market", tags=["行情"])
router.include_router(strategy.router, prefix="/strategies", tags=["策略"])
router.include_router(strategy_logs.router, prefix="/strategies", tags=["策略日志"])
router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
router.include_router(trade.router, prefix="/trade", tags=["交易"])
router.include_router(risk.router, prefix="/risk", tags=["风控"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["看板"])
router.include_router(settings.router, prefix="/settings", tags=["设置"])
router.include_router(watchlist.router, prefix="/market/watchlist", tags=["自选"])
