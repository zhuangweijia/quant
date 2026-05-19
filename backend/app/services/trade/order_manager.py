from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.position import Position
from app.services.trade.base import get_paper_broker
from app.services.trade.broker_factory import get_broker_for_user
from app.core.events import event_bus
import structlog

logger = structlog.get_logger()


async def submit_order(
    db: AsyncSession, user_id: str, payload: dict
) -> Order:
    if payload["order_type"] in ("limit", "stop") and payload.get("price") is None:
        raise ValueError("限价单和止损单必须指定价格")

    if payload["side"] == "sell":
        pos_query = select(Position).where(
            Position.user_id == user_id,
            Position.symbol == payload["symbol"],
        )
        if payload.get("strategy_id"):
            pos_query = pos_query.where(Position.strategy_id == payload["strategy_id"])
        result = await db.execute(pos_query)
        position = result.scalar_one_or_none()
        available = position.qty - position.frozen_qty if position else Decimal("0")
        if available < payload["qty"]:
            raise ValueError(f"持仓不足，可用 {available}，需要 {payload['qty']}")

    if payload["market"] == "a_stock" and payload["side"] == "buy":
        if payload["qty"] % 100 != 0:
            raise ValueError("A股买入数量必须为100的整数倍")

    order = Order(
        user_id=user_id,
        strategy_id=payload.get("strategy_id"),
        symbol=payload["symbol"],
        market=payload["market"],
        side=payload["side"],
        order_type=payload["order_type"],
        qty=payload["qty"],
        price=payload.get("price"),
        status="pending",
    )
    db.add(order)
    await db.flush()

    if payload["side"] == "sell" and payload.get("strategy_id"):
        pos_result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.symbol == payload["symbol"],
                Position.strategy_id == payload["strategy_id"],
            )
        )
        pos = pos_result.scalar_one_or_none()
        if pos:
            pos.frozen_qty += payload["qty"]
            await db.flush()

    broker = await get_broker_for_user(db, user_id, payload.get("market", ""))
    try:
        result = await broker.submit_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            qty=order.qty,
            price=order.price,
        )
        order.broker_order_id = result.get("broker_order_id")
        status = result.get("status", "submitted")

        if status == "filled":
            order.status = "filled"
            order.filled_qty = result.get("filled_qty", order.qty)
            order.filled_price = result.get("filled_price", order.price)
            order.commission = result.get("commission", Decimal("0"))
            await _update_position(db, order)
        elif status == "rejected":
            order.status = "rejected"
            order.error_message = result.get("reason", "被拒绝")
            if payload["side"] == "sell" and payload.get("strategy_id"):
                await _unfreeze_position(db, user_id, payload["symbol"], payload["strategy_id"], payload["qty"])
        else:
            order.status = "submitted"

        await db.flush()

        try:
            await event_bus.publish("trade:order", {
                "user_id": user_id,
                "order_id": str(order.id),
                "status": order.status,
                "symbol": order.symbol,
                "side": order.side,
            })
        except Exception:
            pass

    except Exception as e:
        order.status = "rejected"
        order.error_message = str(e)
        await db.flush()
        raise

    return order


async def cancel_order(db: AsyncSession, user_id: str, order_id: str) -> Order:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise ValueError("订单不存在")
    if order.status not in ("pending", "submitted", "partial_filled"):
        raise ValueError(f"订单状态为 {order.status}，无法撤单")

    if order.broker_order_id:
        broker = await get_broker_for_user(db, user_id, order.market or "")
        await broker.cancel_order(order.broker_order_id)

    if order.side == "sell" and order.strategy_id:
        unfilled = order.qty - (order.filled_qty or Decimal("0"))
        await _unfreeze_position(db, user_id, order.symbol, order.strategy_id, unfilled)

    if order.filled_qty and order.filled_qty > 0:
        order.status = "cancelled"
        await _update_position(db, order)
    else:
        order.status = "cancelled"
    await db.flush()

    try:
        await event_bus.publish("trade:order", {
            "user_id": user_id,
            "order_id": str(order.id),
            "status": "cancelled",
        })
    except Exception:
        pass

    return order


async def close_position(db: AsyncSession, user_id: str, position_id: str) -> Order:
    position = await db.get(Position, position_id)
    if not position or position.user_id != user_id:
        raise ValueError("持仓不存在")

    order = Order(
        user_id=user_id,
        strategy_id=position.strategy_id,
        symbol=position.symbol,
        market=position.market,
        side="sell",
        order_type="market",
        qty=position.qty,
        price=None,
        status="pending",
    )
    db.add(order)
    await db.flush()

    broker = await get_broker_for_user(db, user_id, position.market or "")
    result = await broker.submit_order(
        symbol=order.symbol, side="sell", order_type="market",
        qty=order.qty, price=None,
    )
    order.broker_order_id = result.get("broker_order_id")
    if result.get("status") == "filled":
        order.status = "filled"
        order.filled_qty = result.get("filled_qty", order.qty)
        order.filled_price = result.get("filled_price")
        order.commission = result.get("commission", Decimal("0"))
        await _update_position(db, order)
    else:
        order.status = "submitted"
    await db.flush()
    return order


async def _update_position(db: AsyncSession, order: Order) -> None:
    filled_qty = order.filled_qty or Decimal("0")
    filled_price = order.filled_price or order.price or Decimal("0")
    if filled_qty <= 0:
        return

    if order.side == "buy":
        result = await db.execute(
            select(Position).where(
                Position.user_id == order.user_id,
                Position.strategy_id == order.strategy_id if order.strategy_id else Position.strategy_id.is_(None),
                Position.symbol == order.symbol,
            )
        )
        position = result.scalar_one_or_none()
        if position:
            new_qty = position.qty + filled_qty
            new_avg = (position.avg_price * position.qty + filled_price * filled_qty) / new_qty
            position.qty = new_qty
            position.avg_price = new_avg.quantize(Decimal("0.00000001"))
        else:
            position = Position(
                user_id=order.user_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                market=order.market,
                qty=filled_qty,
                avg_price=filled_price,
            )
            db.add(position)

        from app.services.account_service import get_or_create_account
        account = await get_or_create_account(db, order.user_id)
        cost = filled_price * filled_qty
        commission = order.commission or Decimal("0")
        account.cash -= (cost + commission)

    elif order.side == "sell":
        query = select(Position).where(
            Position.user_id == order.user_id,
            Position.symbol == order.symbol,
        )
        if order.strategy_id:
            query = query.where(Position.strategy_id == order.strategy_id)
        result = await db.execute(query)
        position = result.scalar_one_or_none()
        if position:
            position.qty -= filled_qty
            if position.frozen_qty > 0:
                position.frozen_qty = max(Decimal("0"), position.frozen_qty - filled_qty)
            if position.qty <= 0:
                await db.delete(position)

        from app.services.account_service import get_or_create_account
        account = await get_or_create_account(db, order.user_id)
        proceeds = filled_price * filled_qty
        commission = order.commission or Decimal("0")
        account.cash += (proceeds - commission)

    try:
        await event_bus.publish("trade:position", {
            "user_id": order.user_id,
            "symbol": order.symbol,
            "side": order.side,
            "qty": str(filled_qty),
        })
    except Exception:
        pass


async def _unfreeze_position(
    db: AsyncSession, user_id: str, symbol: str, strategy_id: str | None, qty: Decimal
) -> None:
    query = select(Position).where(
        Position.user_id == user_id,
        Position.symbol == symbol,
    )
    if strategy_id:
        query = query.where(Position.strategy_id == strategy_id)
    result = await db.execute(query)
    position = result.scalar_one_or_none()
    if position and position.frozen_qty > 0:
        position.frozen_qty = max(Decimal("0"), position.frozen_qty - qty)
