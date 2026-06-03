from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.position import Position
from app.models.order import Order
from app.models.strategy import Strategy
from app.models.alert import Alert
from app.models.equity_snapshot import EquitySnapshot
from app.services.market_service import get_cached_prices
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


async def calc_position_values(
    db: AsyncSession, user_id: str,
) -> tuple[Decimal, list[dict]]:
    pos_result = await db.execute(
        select(Position).where(Position.user_id == user_id, Position.qty > 0)
    )
    positions = pos_result.scalars().all()
    if not positions:
        return Decimal("0"), []

    symbols = [(pos.symbol, pos.market) for pos in positions]
    prices = await get_cached_prices(symbols)

    total_value = Decimal("0")
    pos_list: list[dict] = []
    for pos in positions:
        price = prices.get(pos.symbol, pos.avg_price)
        market_value = price * pos.qty
        total_value += market_value
        pos_list.append({
            "symbol": pos.symbol,
            "market": pos.market,
            "qty": pos.qty,
            "avg_price": pos.avg_price,
            "current_price": price,
            "market_value": market_value,
        })
    return total_value, pos_list


async def get_account_info(db: AsyncSession, user_id: str) -> dict:
    account = await get_or_create_account(db, user_id)
    position_value, _ = await calc_position_values(db, user_id)
    total_equity = account.cash + position_value

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_trades = await db.scalar(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.status == "filled",
            Order.created_at >= today_start,
        )
    ) or 0

    running_strategies = await db.scalar(
        select(func.count(Strategy.id)).where(Strategy.user_id == user_id, Strategy.status == "running")
    ) or 0

    total_strategies = await db.scalar(
        select(func.count(Strategy.id)).where(Strategy.user_id == user_id, Strategy.deleted_at.is_(None))
    ) or 0

    unread_alerts = await db.scalar(
        select(func.count(Alert.id)).where(Alert.user_id == user_id, Alert.read == False)
    ) or 0

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_pnl = Decimal("0")
    daily_pnl_pct = Decimal("0")

    snapshot_result = await db.execute(
        select(EquitySnapshot).where(
            EquitySnapshot.user_id == user_id,
        ).order_by(EquitySnapshot.timestamp.desc()).limit(2)
    )
    snapshots = snapshot_result.scalars().all()

    if snapshots:
        latest_snapshot = snapshots[0]
        latest_date = latest_snapshot.timestamp.strftime("%Y-%m-%d")
        if latest_date == today_str and len(snapshots) > 1:
            yesterday = snapshots[1]
            daily_pnl = latest_snapshot.total_equity - yesterday.total_equity
            daily_pnl_pct = (daily_pnl / yesterday.total_equity * 100) if yesterday.total_equity > 0 else Decimal("0")
        elif latest_date != today_str:
            daily_pnl = total_equity - latest_snapshot.total_equity
            daily_pnl_pct = (daily_pnl / latest_snapshot.total_equity * 100) if latest_snapshot.total_equity > 0 else Decimal("0")

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


async def save_equity_snapshot(db: AsyncSession, user_id: str):
    account = await get_or_create_account(db, user_id)
    now = datetime.now(timezone.utc)

    position_value, _ = await calc_position_values(db, user_id)
    total_equity = account.cash + position_value

    hour_key = now.strftime("%Y-%m-%d %H:00")
    existing = await db.execute(
        select(EquitySnapshot).where(
            EquitySnapshot.user_id == user_id,
            EquitySnapshot.timestamp >= hour_key,
            EquitySnapshot.timestamp < (now.replace(minute=0, second=0, microsecond=0) + __import__("datetime").timedelta(hours=1)),
        )
    )
    snapshot = existing.scalar_one_or_none()

    if snapshot:
        snapshot.total_equity = total_equity
        snapshot.cash = account.cash
        snapshot.position_value = position_value
        snapshot.timestamp = now
    else:
        yesterday_eq = account.initial_capital
        prev = await db.execute(
            select(EquitySnapshot).where(
                EquitySnapshot.user_id == user_id,
            ).order_by(EquitySnapshot.timestamp.desc()).limit(1)
        )
        prev_snap = prev.scalar_one_or_none()
        if prev_snap:
            yesterday_eq = prev_snap.total_equity

        daily_pnl = total_equity - yesterday_eq
        snapshot = EquitySnapshot(
            user_id=user_id,
            timestamp=now,
            total_equity=total_equity,
            cash=account.cash,
            position_value=position_value,
            daily_pnl=daily_pnl,
        )
        db.add(snapshot)

    await db.flush()
