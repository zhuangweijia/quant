from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, Request
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.models.order import Order
from app.models.position import Position
from app.schemas.common import ResponseBase, PageResponse
from app.schemas.trade import OrderRequest, OrderResponse, PositionResponse, AccountInfoResponse
from app.services.trade.order_manager import submit_order, cancel_order, close_position
from app.services.risk_service import evaluate_risk
from app.services.account_service import get_account_info
from app.services.audit_service import log_action, extract_request_info

router = APIRouter()


@router.post("/order", response_model=ResponseBase[OrderResponse], status_code=201)
async def create_order(
    user: CurrentUser,
    db: DBSession,
    payload: OrderRequest,
    request: Request,
):
    order_data = {
        "symbol": payload.symbol,
        "market": payload.market,
        "side": payload.side,
        "order_type": payload.order_type,
        "qty": payload.qty,
        "price": payload.price,
        "strategy_id": str(payload.strategy_id) if payload.strategy_id else None,
    }

    passed, reason = await evaluate_risk(db, user.id, order_data)
    if not passed:
        raise HTTPException(status_code=400, detail=f"风控拦截: {reason}")

    try:
        order = await submit_order(db, user.id, order_data)
        await db.refresh(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="trade.order_submit", resource_type="order", resource_id=str(order.id), detail={"symbol": payload.symbol, "side": payload.side, "order_type": payload.order_type, "qty": str(payload.qty)}, ip_address=ip, user_agent=ua)

    return ResponseBase(data=OrderResponse.model_validate(order))


@router.delete("/order/{order_id}", response_model=ResponseBase[None])
async def api_cancel_order(
    user: CurrentUser,
    db: DBSession,
    order_id: UUID,
    request: Request,
):
    try:
        await cancel_order(db, user.id, str(order_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="trade.order_cancel", resource_type="order", resource_id=str(order_id), ip_address=ip, user_agent=ua)

    return ResponseBase()


@router.get("/orders", response_model=ResponseBase[PageResponse[OrderResponse]])
async def list_orders(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    symbol: str | None = Query(None),
    market: str | None = Query(None),
    side: str | None = Query(None),
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
    if side:
        query = query.where(Order.side == side)
        count_query = count_query.where(Order.side == side)
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


@router.post("/positions/close", response_model=ResponseBase[OrderResponse])
async def api_close_position(
    user: CurrentUser,
    db: DBSession,
    request: Request,
    position_id: str = Query(...),
):
    try:
        order = await close_position(db, user.id, position_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="trade.position_close", resource_type="position", resource_id=position_id, detail={"symbol": order.symbol, "qty": str(order.qty)}, ip_address=ip, user_agent=ua)

    return ResponseBase(data=OrderResponse.model_validate(order))


@router.get("/account", response_model=ResponseBase[dict])
async def get_account(
    user: CurrentUser,
    db: DBSession,
):
    info = await get_account_info(db, user.id)
    return ResponseBase(data=info)
