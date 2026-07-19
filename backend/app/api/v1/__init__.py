from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analysis,
    auth,
    dashboard,
    market,
    model,
    portfolio,
    ranking,
    settings,
    setup,
    stock_detail,
    watchlist,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(market.router, prefix="/market", tags=["行情"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["看板"])
router.include_router(settings.router, prefix="/settings", tags=["设置"])
router.include_router(watchlist.router, prefix="/market/watchlist", tags=["自选"])
router.include_router(admin.router, prefix="/admin", tags=["管理"])
router.include_router(ranking.router, prefix="/rankings", tags=["排名"])
router.include_router(stock_detail.router, prefix="/stocks", tags=["个股"])
router.include_router(model.router, prefix="/model", tags=["模型"])
router.include_router(analysis.router, prefix="/analysis", tags=["分析"])
router.include_router(setup.router, prefix="/setup", tags=["首次配置"])
router.include_router(portfolio.router, prefix="/portfolio", tags=["投资组合"])
