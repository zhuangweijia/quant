from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_rule import RiskRule
from app.models.alert import Alert
from app.models.position import Position
from app.services.account_service import get_or_create_account
from app.services.market_service import get_provider
from app.core.events import event_bus
import structlog

logger = structlog.get_logger()


class RiskRuleEvaluator(ABC):
    @abstractmethod
    async def evaluate(self, order: dict, context: dict) -> tuple[bool, str]:
        ...


class MaxPositionValueEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.max_value = float(params.get("max_value", 0))

    async def evaluate(self, order, context):
        if order["side"] != "buy":
            return True, ""
        current_value = context.get("position_values", {}).get(order["symbol"], 0)
        price = float(order.get("price") or context.get("current_price", 0))
        order_value = float(order["qty"]) * price
        if current_value + order_value > self.max_value:
            return False, f"单标的持仓金额超限: {current_value + order_value:.2f} > {self.max_value}"
        return True, ""


class MaxPositionRatioEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.max_ratio = float(params.get("max_ratio", 1))

    async def evaluate(self, order, context):
        if order["side"] != "buy":
            return True, ""
        total_equity = context.get("total_equity", 0)
        if total_equity <= 0:
            return True, ""
        price = float(order.get("price") or context.get("current_price", 0))
        order_value = float(order["qty"]) * price
        current_position = context.get("total_position_value", 0)
        new_ratio = (current_position + order_value) / total_equity
        if new_ratio > self.max_ratio:
            return False, f"总仓位占比超限: {new_ratio:.2%} > {self.max_ratio:.2%}"
        return True, ""


class DailyLossLimitEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.max_daily_loss = float(params.get("max_daily_loss", 0))

    async def evaluate(self, order, context):
        daily_loss = context.get("daily_loss", 0)
        if abs(daily_loss) >= self.max_daily_loss:
            return False, f"日亏损已达限额: {abs(daily_loss):.2f} >= {self.max_daily_loss}"
        return True, ""


class DailyTradeLimitEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.max_trades = int(params.get("max_trades", 999))

    async def evaluate(self, order, context):
        daily_trades = context.get("daily_trades", 0)
        if daily_trades >= self.max_trades:
            return False, f"日交易次数已达上限: {daily_trades} >= {self.max_trades}"
        return True, ""


class BlacklistEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.symbols = [s.upper() for s in params.get("symbols", [])]

    async def evaluate(self, order, context):
        if order["symbol"].upper() in self.symbols:
            return False, f"标的 {order['symbol']} 在交易黑名单中"
        return True, ""


class MaxOrderAmountEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.max_amount = float(params.get("max_amount", 0))

    async def evaluate(self, order, context):
        price = float(order.get("price") or context.get("current_price", 0))
        amount = float(order["qty"]) * price
        if amount > self.max_amount:
            return False, f"单笔下单金额超限: {amount:.2f} > {self.max_amount}"
        return True, ""


RULE_EVALUATORS = {
    "max_position_value": MaxPositionValueEvaluator,
    "max_position_ratio": MaxPositionRatioEvaluator,
    "daily_loss_limit": DailyLossLimitEvaluator,
    "daily_trade_limit": DailyTradeLimitEvaluator,
    "blacklist": BlacklistEvaluator,
    "max_order_amount": MaxOrderAmountEvaluator,
    "stop_loss": None,
    "take_profit": None,
    "max_total_position": MaxPositionRatioEvaluator,
}


async def build_context(db: AsyncSession, user_id: str, symbol: str) -> dict:
    account = await get_or_create_account(db, user_id)
    pos_result = await db.execute(
        select(Position).where(Position.user_id == user_id, Position.qty > 0)
    )
    positions = pos_result.scalars().all()

    total_position_value = Decimal("0")
    position_values = {}
    for pos in positions:
        provider = get_provider(pos.market)
        try:
            latest = await provider.get_latest_price(pos.symbol)
            price = Decimal(latest.get("price", "0"))
            value = price * pos.qty
        except Exception:
            value = pos.avg_price * pos.qty
        position_values[pos.symbol] = float(value)
        total_position_value += value

    current_price = Decimal("0")
    provider = get_provider("mock")
    try:
        latest = await provider.get_latest_price(symbol)
        current_price = Decimal(latest.get("price", "0"))
    except Exception:
        pass

    return {
        "total_equity": float(account.cash + total_position_value),
        "cash": float(account.cash),
        "total_position_value": float(total_position_value),
        "position_values": position_values,
        "current_price": float(current_price),
        "daily_loss": 0,
        "daily_trades": 0,
    }


async def evaluate_risk(db: AsyncSession, user_id: str, order: dict) -> tuple[bool, str]:
    query = select(RiskRule).where(
        RiskRule.user_id == user_id,
        RiskRule.enabled == True,
    ).order_by(RiskRule.priority.asc())
    result = await db.execute(query)
    rules = result.scalars().all()

    if not rules:
        return True, ""

    context = await build_context(db, user_id, order.get("symbol", ""))

    for rule in rules:
        evaluator_cls = RULE_EVALUATORS.get(rule.rule_type)
        if evaluator_cls is None:
            continue
        evaluator = evaluator_cls(rule.params)
        passed, reason = await evaluator.evaluate(order, context)
        if not passed:
            await _create_alert(
                db, user_id, rule.strategy_id,
                "warning", "风控拦截",
                f"订单被拦截: {reason}",
            )
            return False, reason

    return True, ""


async def _create_alert(
    db: AsyncSession, user_id: str, strategy_id: str | None,
    level: str, title: str, message: str,
) -> Alert:
    alert = Alert(
        user_id=user_id,
        strategy_id=strategy_id,
        level=level,
        title=title,
        message=message,
    )
    db.add(alert)
    await db.flush()

    try:
        await event_bus.publish("risk:alert", {
            "user_id": user_id,
            "alert_id": str(alert.id),
            "level": level,
            "title": title,
            "message": message,
        })
    except Exception:
        pass

    return alert


async def mark_all_alerts_read(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(Alert).where(Alert.user_id == user_id, Alert.read == False)
    )
    alerts = result.scalars().all()
    count = 0
    for alert in alerts:
        alert.read = True
        count += 1
    await db.flush()
    return count


async def get_unread_count(db: AsyncSession, user_id: str) -> int:
    from sqlalchemy import func
    result = await db.scalar(
        select(func.count(Alert.id)).where(Alert.user_id == user_id, Alert.read == False)
    )
    return result or 0
