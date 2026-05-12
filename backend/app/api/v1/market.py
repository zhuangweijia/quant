from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.market import KlineData

router = APIRouter()


@router.get("/symbols", response_model=ResponseBase[list[dict]])
async def search_symbols(
    user: CurrentUser,
    keyword: str = Query(..., min_length=1),
    market: str | None = Query(None),
):
    return ResponseBase(data=[], message="行情模块待实现")


@router.get("/klines", response_model=ResponseBase[list[KlineData]])
async def get_klines(
    user: CurrentUser,
    symbol: str = Query(...),
    market: str = Query(...),
    timeframe: str = Query("1d"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    return ResponseBase(data=[], message="行情模块待实现")
