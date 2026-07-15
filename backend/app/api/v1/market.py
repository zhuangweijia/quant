from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import ResponseBase
from app.schemas.market import KlineData, SymbolInfo
from app.services.market_service import get_provider

router = APIRouter()


@router.get("/symbols", response_model=ResponseBase[list[SymbolInfo]])
async def search_symbols(
    user: CurrentUser,
    keyword: str = Query(..., min_length=1),
    market: str | None = Query(None),
):
    provider = get_provider(market or "mock")
    results = await provider.search_symbols(keyword)
    if market:
        results = [r for r in results if r.get("market") == market]
    return ResponseBase(data=[SymbolInfo(**r) for r in results])


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
    provider = get_provider(market)
    raw = await provider.get_klines(symbol, timeframe, start, end, limit)
    data = []
    for r in raw:
        data.append(
            KlineData(
                timestamp=r["timestamp"],
                open=r["open"],
                high=r["high"],
                low=r["low"],
                close=r["close"],
                volume=r["volume"],
            )
        )
    return ResponseBase(data=data)


@router.get("/tick", response_model=ResponseBase[dict])
async def get_latest_tick(
    user: CurrentUser,
    symbol: str = Query(...),
    market: str = Query("crypto"),
):
    provider = get_provider(market)
    data = await provider.get_latest_price(symbol)
    return ResponseBase(data=data)
