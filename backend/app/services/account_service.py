from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.position import Position
from app.models.order import Order
from app.models.strategy import Strategy
from app.models.alert import Alert
from app.services.market_service import get_provider
import structlog

logger = structlog.get_logger()


async def get_or_create_account(db: AsyncSession, user_id: str) -> Account:
    result = await db.execute(
        select(Account).where(Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        account = Account(
            user_id=user_id,
            mode="paper",
            cash=Decimal("1000000"),
            initial_capital=Decimal("1000000"),
        )
        db.add(account)
        await db.flush()
    return account


async def get_account_info(db: AsyncSession, user_id: str) -> dict:
    account = await get_or_create_account(db, user_id)

    pos_result = await db.execute(
        select(Position).where(Position.user_id == user_id, Position.qty > 0)
    )
    positions = pos_result.scalars().all()

    position_value = Decimal("0")
    for pos in positions:
        provider = get_provider(pos.market)
        try:
            latest = await provider.get_latest_price(pos.symbol)
            price = Decimal(latest.get("price", "0"))
            position_value += price * pos.qty
        except Exception:
            position_value += pos.avg_price * pos.qty

    total_equity = account.cash + position_value

    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d") + "T00:00:00Z"

    today_order_result = await db.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.status == "filled",
            Order.created_at >= today_start,
        )
    )
    today_trades = len(today_order_result.scalars().all())

    running_result = await db.execute(
        select(Strategy).where(Strategy.user_id == user_id, Strategy.status == "running")
    )
    running_strategies = len(running_result.scalars().all())

    total_result = await db.execute(
        select(Strategy).where(Strategy.user_id == user_id, Strategy.deleted_at.is_(None))
    )
    total_strategies = len(total_result.scalars().all())

    unread_result = await db.execute(
        select(Alert).where(Alert.user_id == user_id, Alert.read == False)
    )
    unread_alerts = len(unread_result.scalars().all())

    daily_pnl = Decimal("0")
    daily_pnl_pct = Decimal("0")
    total_pnl = total_equity - account.initial_capital
    total_pnl_pct = (total_pnl / account.initial_capital * 100) if account.initial_capital > 0 else Decimal("0")

    return {
        "total_equity": total_equity,
        "cash": account.cash,
        "position_value": position_value,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "running_strategies": running_strategies,
        "total_strategies": total_strategies,
        "today_trades": today_trades,
        "unread_alerts": unread_alerts,
        "mode": account.mode,
    }
