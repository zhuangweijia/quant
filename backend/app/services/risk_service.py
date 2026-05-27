from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_rule import RiskRule
from app.models.alert import Alert
from app.models.position import Position
from app.models.order import Order
from app.models.risk_event import RiskEvent
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


class StopLossEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.stop_type = params.get("stop_type", "fixed")
        self.stop_value = float(params.get("value", 0))
        self.trail_percent = float(params.get("trail_percent", 0))

    async def evaluate(self, order, context):
        if order["side"] != "sell":
            return True, ""
        symbol = order["symbol"]
        current_price = context.get("current_price", 0)
        if not current_price:
            return True, ""

        if self.stop_type == "fixed":
            if current_price <= self.stop_value:
                return False, f"已触发止损: 当前价 {current_price} <= {self.stop_value}"

        elif self.stop_type == "percent":
            pos_avg_price = context.get("position_avg_prices", {}).get(symbol, 0)
            if pos_avg_price > 0:
                drop = (pos_avg_price - current_price) / pos_avg_price * 100
                if drop >= self.stop_value:
                    return False, f"已触发百分比止损: 跌幅 {drop:.2f}%"

        elif self.stop_type == "trailing":
            peak = context.get("position_peaks", {}).get(symbol, 0)
            if peak > 0:
                drawdown = (peak - current_price) / peak * 100
                if drawdown >= self.trail_percent:
                    return False, f"已触发移动止损: 回撤 {drawdown:.2f}%"

        return True, ""


class TakeProfitEvaluator(RiskRuleEvaluator):
    def __init__(self, params: dict):
        self.take_type = params.get("take_type", "fixed")
        self.take_value = float(params.get("value", 0))

    async def evaluate(self, order, context):
        if order["side"] != "sell":
            return True, ""
        current_price = context.get("current_price", 0)
        if not current_price:
            return True, ""

        if self.take_type == "fixed":
            if current_price >= self.take_value:
                return False, f"已触发止盈: 当前价 {current_price} >= {self.take_value}"

        elif self.take_type == "percent":
            symbol = order["symbol"]
            pos_avg_price = context.get("position_avg_prices", {}).get(symbol, 0)
            if pos_avg_price > 0:
                gain = (current_price - pos_avg_price) / pos_avg_price * 100
                if gain >= self.take_value:
                    return False, f"已触发百分比止盈: 涨幅 {gain:.2f}%"

        return True, ""


RULE_EVALUATORS = {
    "max_position_value": MaxPositionValueEvaluator,
    "max_position_ratio": MaxPositionRatioEvaluator,
    "daily_loss_limit": DailyLossLimitEvaluator,
    "daily_trade_limit": DailyTradeLimitEvaluator,
    "blacklist": BlacklistEvaluator,
    "max_order_amount": MaxOrderAmountEvaluator,
    "stop_loss": StopLossEvaluator,
    "take_profit": TakeProfitEvaluator,
    "max_total_position": MaxPositionRatioEvaluator,
}


async def build_context(db: AsyncSession, user_id: str, symbol: str, market: str = "") -> dict:
    account = await get_or_create_account(db, user_id)
    pos_result = await db.execute(
        select(Position).where(Position.user_id == user_id, Position.qty > 0)
    )
    positions = pos_result.scalars().all()

    total_position_value = Decimal("0")
    position_values = {}
    position_avg_prices = {}
    position_markets: dict[str, str] = {}
    for pos in positions:
        provider = get_provider(pos.market)
        position_markets[pos.symbol] = pos.market
        position_avg_prices[pos.symbol] = float(pos.avg_price)
        try:
            latest = await provider.get_latest_price(pos.symbol)
            price = Decimal(latest.get("price", "0"))
            value = price * pos.qty
        except Exception:
            value = pos.avg_price * pos.qty
        position_values[pos.symbol] = float(value)
        total_position_value += value

    current_price = Decimal("0")
    if symbol:
        effective_market = market or position_markets.get(symbol, "mock")
        try:
            provider = get_provider(effective_market)
            latest = await provider.get_latest_price(symbol)
            current_price = Decimal(latest.get("price", "0"))
        except Exception:
            pass

    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d") + "T00:00:00+00:00"

    daily_trades_result = await db.scalar(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.status == "filled",
            Order.created_at >= today_start,
        )
    )

    daily_filled = await db.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.status == "filled",
            Order.side == "sell",
            Order.created_at >= today_start,
        )
    )
    daily_loss = Decimal("0")
    for order in daily_filled.scalars().all():
        if order.filled_price and order.filled_qty:
            pos_q = await db.execute(
                select(Position).where(
                    Position.user_id == user_id,
                    Position.symbol == order.symbol,
                )
            )
            pos = pos_q.scalar_one_or_none()
            if pos:
                pnl = (order.filled_price - pos.avg_price) * order.filled_qty
                daily_loss += pnl

    return {
        "total_equity": float(account.cash + total_position_value),
        "cash": float(account.cash),
        "total_position_value": float(total_position_value),
        "position_values": position_values,
        "position_avg_prices": position_avg_prices,
        "position_peaks": position_values,
        "current_price": float(current_price),
        "daily_loss": float(daily_loss),
        "daily_trades": daily_trades_result or 0,
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

    context = await build_context(db, user_id, order.get("symbol", ""), order.get("market", ""))

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
            await _create_risk_event(db, user_id, rule, order, "block", reason)
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


async def _create_risk_event(
    db: AsyncSession, user_id: str, rule: RiskRule,
    order: dict, result: str, reason: str,
) -> RiskEvent:
    event = RiskEvent(
        user_id=user_id,
        strategy_id=rule.strategy_id,
        rule_id=str(rule.id),
        rule_type=rule.rule_type,
        result=result,
        detail={"reason": reason, "order": order},
    )
    db.add(event)
    await db.flush()
    return event


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
    result = await db.scalar(
        select(func.count(Alert.id)).where(Alert.user_id == user_id, Alert.read == False)
    )
    return result or 0


async def check_stop_loss_take_profit(db: AsyncSession, user_id: str):
    rules_result = await db.execute(
        select(RiskRule).where(
            RiskRule.user_id == user_id,
            RiskRule.enabled == True,
            RiskRule.rule_type.in_(["stop_loss", "take_profit"]),
        )
    )
    rules = rules_result.scalars().all()
    if not rules:
        return

    pos_result = await db.execute(
        select(Position).where(Position.user_id == user_id, Position.qty > 0)
    )
    positions = pos_result.scalars().all()

    for pos in positions:
        provider = get_provider(pos.market)
        try:
            latest = await provider.get_latest_price(pos.symbol)
            current_price = float(latest.get("price", "0"))
        except Exception:
            continue

        for rule in rules:
            if rule.strategy_id and str(rule.strategy_id) != str(pos.strategy_id):
                continue

            should_close = False
            reason = ""

            if rule.rule_type == "stop_loss":
                stop_type = rule.params.get("stop_type", "fixed")
                if stop_type == "fixed":
                    stop_price = float(rule.params.get("value", 0))
                    if current_price <= stop_price:
                        should_close = True
                        reason = f"触发止损: 当前价 {current_price} <= 止损价 {stop_price}"
                elif stop_type == "percent":
                    entry_price = float(pos.avg_price)
                    drop_pct = float(rule.params.get("value", 5))
                    if entry_price > 0:
                        drop = (entry_price - current_price) / entry_price * 100
                        if drop >= drop_pct:
                            should_close = True
                            reason = f"触发百分比止损: 跌幅 {drop:.2f}% >= {drop_pct}%"

            elif rule.rule_type == "take_profit":
                take_type = rule.params.get("take_type", "fixed")
                if take_type == "fixed":
                    take_price = float(rule.params.get("value", 0))
                    if current_price >= take_price:
                        should_close = True
                        reason = f"触发止盈: 当前价 {current_price} >= 止盈价 {take_price}"
                elif take_type == "percent":
                    entry_price = float(pos.avg_price)
                    gain_pct = float(rule.params.get("value", 10))
                    if entry_price > 0:
                        gain = (current_price - entry_price) / entry_price * 100
                        if gain >= gain_pct:
                            should_close = True
                            reason = f"触发百分比止盈: 涨幅 {gain:.2f}% >= {gain_pct}%"

            if should_close:
                try:
                    from app.services.trade.order_manager import close_position
                    await close_position(db, user_id, str(pos.id))
                    await _create_alert(db, user_id, rule.strategy_id, "warning", "自动平仓", reason)
                    await db.commit()
                except Exception as e:
                    logger.error("risk.auto_close_failed", error=str(e))
