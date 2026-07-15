from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.watchlist import UserWatchlist
from app.schemas.common import ResponseBase

router = APIRouter()


class WatchlistItem(BaseModel):
    id: str
    symbol: str
    market: str
    sort_order: int

    model_config = {"from_attributes": True}


class WatchlistAddRequest(BaseModel):
    symbol: str
    market: str
    sort_order: int = 0


@router.get("", response_model=ResponseBase[list[WatchlistItem]])
async def get_watchlist(user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(UserWatchlist)
        .where(UserWatchlist.user_id == user.id)
        .order_by(UserWatchlist.sort_order.asc())
    )
    items = result.scalars().all()
    return ResponseBase(data=[WatchlistItem.model_validate(w) for w in items])


@router.post("", response_model=ResponseBase[WatchlistItem], status_code=201)
async def add_to_watchlist(user: CurrentUser, db: DBSession, payload: WatchlistAddRequest):
    existing = await db.execute(
        select(UserWatchlist).where(
            UserWatchlist.user_id == user.id,
            UserWatchlist.symbol == payload.symbol,
            UserWatchlist.market == payload.market,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已在该自选列表中")

    item = UserWatchlist(
        user_id=user.id,
        symbol=payload.symbol,
        market=payload.market,
        sort_order=payload.sort_order,
    )
    db.add(item)
    await db.flush()
    return ResponseBase(data=WatchlistItem.model_validate(item))


@router.delete("/{item_id}", response_model=ResponseBase[None])
async def remove_from_watchlist(user: CurrentUser, db: DBSession, item_id: str):
    item = await db.get(UserWatchlist, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="自选项不存在")
    await db.delete(item)
    await db.flush()
    return ResponseBase()
