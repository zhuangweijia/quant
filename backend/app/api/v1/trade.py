from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func
from decimal import Decimal

from app.api.deps import CurrentUser, DBSession
from app.models.order import Order
from app.models.position import Position
from app.schemas.common import ResponseBase, PageResponse
from app.schemas.trade import OrderRequest, OrderResponse, PositionResponse

router = APIRouter()


@router.post("/order", response_model=ResponseBase[OrderResponse], status_code=201)
async def submit_order(
    user: CurrentUser,
    db: DBSession,
    payload: OrderRequest,
):
    if payload.order_type in ("limit", "stop") and payload.price is None:
        raise HTTPException(status_code=400, detail="限价单和止损单必须指定价格")

    if payload.side == "sell":
        pos_query = select(Position).where(
            Position.user_id == user.id,
            Position.symbol == payload.symbol,
        )
        if payload.strategy_id:
            pos_query = pos_query.where(Position.strategy_id == payload.strategy_id)
        result = await db.execute(pos_query)
        position = result.scalar_one_or_none()
        if not position or position.qty < payload.qty:
            raise HTTPException(status_code=400, detail="持仓不足")

    order = Order(
        user_id=user.id,
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        market=payload.market,
        side=payload.side,
        order_type=payload.order_type,
        qty=payload.qty,
        price=payload.price,
        status="pending",
    )
    db.add(order)
    await db.flush()
    return ResponseBase(data=OrderResponse.model_validate(order))


@router.delete("/order/{order_id}", response_model=ResponseBase[None])
async def cancel_order(
    user: CurrentUser,
    db: DBSession,
    order_id: UUID,
):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ("pending", "submitted", "partial_filled"):
        raise HTTPException(status_code=400, detail="订单状态不允许撤单")

    order.status = "cancelled"
    await db.flush()
    return ResponseBase()


@router.get("/orders", response_model=ResponseBase[PageResponse[OrderResponse]])
async def list_orders(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    symbol: str | None = Query(None),
    market: str | None = Query(None),
    order_status: str | None = Query(None, alias="status"),
):
    query = select(Order).where(Order.user_id == user.id)
    count_query = select(func.count(Order.id)).where(Order.user_id == user.id)

    if symbol:
        query = query.where(Order.symbol == symbol)
        count_query = count_query.where(Order.symbol == symbol)
    if market:
        query = query.where(Order.market == market)
        count_query = count_query.where(Order.market == market)
    if order_status:
        query = query.where(Order.status == order_status)
        count_query = count_query.where(Order.status == order_status)

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=PageResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/positions", response_model=ResponseBase[list[PositionResponse]])
async def list_positions(
    user: CurrentUser,
    db: DBSession,
):
    result = await db.execute(
        select(Position).where(Position.user_id == user.id, Position.qty > 0)
    )
    positions = result.scalars().all()
    return ResponseBase(
        data=[PositionResponse.model_validate(p) for p in positions]
    )
