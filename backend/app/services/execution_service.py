from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.models.advice import AdviceItem, DailyAdvice
from app.models.daily_bar import DailyBar
from app.models.execution import ExecutionMutation, ExecutionRecord
from app.models.portfolio import Portfolio, PortfolioEvent, PortfolioSnapshot, Position
from app.schemas.advice import (
    AdviceItemResponse,
    ExecutionRecordResponse,
    ExecutionResponse,
)
from app.services.audit_service import log_action
from app.services.portfolio_service import value_positions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

MONEY_QUANTUM = Decimal("0.0001")
HANDLED_ITEM_STATUSES = {"executed", "skipped", "expired"}


def _money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM)


def _request_metadata(request_meta: tuple[str | None, str | None] | None) -> dict[str, Any]:
    ip_address, user_agent = request_meta or (None, None)
    return {"ip_address": ip_address, "user_agent": user_agent}


def _conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


@dataclass
class LockedExecution:
    item: AdviceItem
    advice: DailyAdvice
    portfolio: Portfolio
    position: Position | None
    record: ExecutionRecord | None
    advice_items: list[AdviceItem]


@dataclass(frozen=True)
class SnapshotPositionInput:
    symbol: str
    quantity: int
    average_cost: Decimal


def _owned_item_lock_statement(user_id: Any, item_id: Any):
    return (
        select(DailyAdvice)
        .join(AdviceItem, AdviceItem.advice_id == DailyAdvice.id)
        .where(AdviceItem.id == item_id, DailyAdvice.user_id == user_id)
        .with_for_update(of=DailyAdvice)
    )


class ExecutionRepository:
    """Locked, user-scoped persistence for manual advice executions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_mutation(self, user_id: Any, item_id: Any, idempotency_key: str):
        result = await self.db.execute(
            select(
                ExecutionMutation,
                ExecutionRecord.user_id,
                ExecutionRecord.advice_item_id,
            )
            .join(ExecutionRecord, ExecutionRecord.id == ExecutionMutation.execution_id)
            .where(ExecutionMutation.idempotency_key == idempotency_key)
        )
        row = result.one_or_none()
        if row is None:
            return None
        mutation, owner_id, mutation_item_id = row
        if owner_id != user_id or mutation_item_id != item_id:
            raise _conflict(
                "idempotency_key_conflict",
                "该幂等键已用于其他执行请求，请更换后重试",
            )
        return mutation

    def response_from_state(self, state: dict[str, Any]) -> ExecutionResponse:
        return ExecutionResponse.model_validate(state)

    async def lock_owned_item(self, user_id: Any, item_id: Any) -> LockedExecution | None:
        advice_result = await self.db.execute(_owned_item_lock_statement(user_id, item_id))
        advice = advice_result.scalar_one_or_none()
        if advice is None:
            return None

        advice_items_result = await self.db.execute(
            select(AdviceItem)
            .where(AdviceItem.advice_id == advice.id)
            .order_by(AdviceItem.created_at, AdviceItem.symbol)
            .with_for_update()
        )
        advice_items = list(advice_items_result.scalars().all())
        item = next((candidate for candidate in advice_items if candidate.id == item_id), None)
        if item is None:
            return None

        portfolio_result = await self.db.execute(
            select(Portfolio)
            .where(
                Portfolio.id == advice.portfolio_id,
                Portfolio.user_id == user_id,
            )
            .with_for_update()
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if portfolio is None:
            return None

        position_result = await self.db.execute(
            select(Position)
            .where(
                Position.portfolio_id == portfolio.id,
                Position.symbol == item.symbol,
            )
            .with_for_update()
        )
        position = position_result.scalar_one_or_none()
        record_result = await self.db.execute(
            select(ExecutionRecord)
            .where(
                ExecutionRecord.advice_item_id == item.id,
                ExecutionRecord.user_id == user_id,
            )
            .with_for_update()
        )
        record = record_result.scalar_one_or_none()
        return LockedExecution(item, advice, portfolio, position, record, advice_items)

    async def latest_market_date(self) -> date | None:
        return await self.db.scalar(select(func.max(DailyBar.trade_date)))

    async def current_execution_event(self, execution_id: Any) -> PortfolioEvent | None:
        reversal = aliased(PortfolioEvent)
        reversed_event_exists = exists(
            select(reversal.id).where(reversal.reversal_of_id == PortfolioEvent.id)
        )
        result = await self.db.execute(
            select(PortfolioEvent)
            .where(
                PortfolioEvent.source_type == "advice_execution",
                PortfolioEvent.source_id == str(execution_id),
                PortfolioEvent.reversal_of_id.is_(None),
                ~reversed_event_exists,
            )
            .order_by(PortfolioEvent.created_at.desc(), PortfolioEvent.id.desc())
        )
        return result.scalars().first()

    async def has_later_symbol_event(
        self,
        *,
        portfolio_id: Any,
        symbol: str,
        anchor: datetime,
        execution_id: Any,
    ) -> bool:
        count = await self.db.scalar(
            select(func.count(PortfolioEvent.id)).where(
                PortfolioEvent.portfolio_id == portfolio_id,
                or_(
                    PortfolioEvent.symbol == symbol,
                    PortfolioEvent.event_type == "reconcile",
                ),
                PortfolioEvent.created_at >= anchor,
                or_(
                    PortfolioEvent.source_type.is_(None),
                    PortfolioEvent.source_type != "advice_execution",
                    PortfolioEvent.source_id.is_(None),
                    PortfolioEvent.source_id != str(execution_id),
                ),
            )
        )
        return bool(count)

    async def create_snapshot(
        self,
        portfolio: Portfolio,
        *,
        reason: str,
        execution_id: uuid.UUID,
        captured_at: datetime,
    ) -> PortfolioSnapshot:
        position_result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .order_by(Position.symbol)
        )
        positions = [position for position in position_result.scalars().all() if position.quantity]
        valuations = await value_positions(
            self.db,
            [
                SnapshotPositionInput(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    average_cost=_money(
                        Decimal(position.total_cost) / Decimal(position.quantity)
                    ),
                )
                for position in positions
            ],
        )
        market_value = sum((valuation.market_value for valuation in valuations), Decimal("0"))
        warnings = [
            valuation.valuation_warning
            for valuation in valuations
            if valuation.valuation_warning
        ]
        snapshot = PortfolioSnapshot(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            reason=reason,
            reference_type="execution_record",
            reference_id=str(execution_id),
            cash=_money(portfolio.cash),
            market_value=_money(market_value),
            total_asset=_money(Decimal(portfolio.cash) + market_value),
            price_date=(
                None
                if warnings
                else max((valuation.price_date for valuation in valuations), default=None)
            ),
            positions=[
                {
                    "symbol": valuation.symbol,
                    "quantity": valuation.quantity,
                    "average_cost": str(_money(valuation.average_cost)),
                    "latest_close": str(_money(valuation.latest_close)),
                    "price_date": (
                        valuation.price_date.isoformat()
                        if valuation.price_date is not None
                        else None
                    ),
                    "market_value": str(_money(valuation.market_value)),
                    "valuation_warning": valuation.valuation_warning,
                }
                for valuation in valuations
            ],
            captured_at=captured_at,
            created_at=captured_at,
            updated_at=captured_at,
        )
        self.db.add(snapshot)
        return snapshot

    def create_event(
        self,
        portfolio: Portfolio,
        item: AdviceItem,
        record: ExecutionRecord,
        *,
        event_type: str,
        quantity_delta: int,
        cash_delta: Decimal,
        total_cost_delta: Decimal,
        occurred_at: datetime,
        created_at: datetime,
        revision: int,
        reversal_of_id: uuid.UUID | None = None,
    ) -> PortfolioEvent:
        event = PortfolioEvent(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            symbol=item.symbol,
            event_type=event_type,
            quantity_delta=quantity_delta,
            cash_delta=_money(cash_delta),
            source_type="advice_execution",
            source_id=str(record.id),
            reversal_of_id=reversal_of_id,
            payload={
                "revision": revision,
                "total_cost_delta": str(_money(total_cost_delta)),
            },
            occurred_at=occurred_at,
            created_at=created_at,
            updated_at=created_at,
        )
        self.db.add(event)
        return event

    async def flush(self) -> None:
        await self.db.flush()


def _record_response(record: ExecutionRecord) -> ExecutionRecordResponse:
    return ExecutionRecordResponse(
        id=record.id,
        disposition=record.disposition,
        quantity=record.quantity,
        price=record.price,
        fee=record.fee,
        executed_at=record.executed_at,
        reason=record.reason or "",
        within_price_band=record.within_price_band,
        revision=record.revision,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _item_response(item: AdviceItem, record: ExecutionRecord) -> AdviceItemResponse:
    return AdviceItemResponse(
        id=item.id,
        symbol=item.symbol,
        name=item.name,
        industry=item.industry,
        action=item.action,
        status=item.status,
        current_quantity=item.current_quantity,
        target_quantity=item.target_quantity,
        delta_quantity=item.delta_quantity,
        current_average_cost=None,
        current_weight=item.current_weight,
        target_weight=item.target_weight,
        reference_price=item.reference_price,
        price_tolerance=item.price_tolerance,
        score=item.score,
        rank=item.rank,
        confidence=item.confidence,
        positive_factors=item.positive_factors,
        risks=item.risks,
        invalidation_conditions=item.invalidation_conditions,
        constraint_notes=item.constraint_notes,
        execution=_record_response(record),
    )


def _response(item: AdviceItem, record: ExecutionRecord, advice_state: str) -> ExecutionResponse:
    return ExecutionResponse(
        item=_item_response(item, record),
        advice_state=advice_state,
    )


def _execution_state(
    item: AdviceItem, record: ExecutionRecord | None, advice_state: str
) -> dict[str, Any] | None:
    if record is None:
        return None
    return _response(item, record, advice_state).model_dump(mode="json")


def _trade_deltas(
    item: AdviceItem,
    payload: Any,
    *,
    base_quantity: int,
    base_total_cost: Decimal,
) -> tuple[int, Decimal, Decimal]:
    advised_quantity = abs(item.delta_quantity)
    if advised_quantity == 0:
        raise HTTPException(status_code=422, detail="持有建议不能记录成交")
    if payload.quantity > advised_quantity:
        raise HTTPException(status_code=422, detail="成交数量不能超过建议调整数量")
    if payload.disposition == "executed" and payload.quantity != advised_quantity:
        raise HTTPException(status_code=422, detail="全部执行必须填写完整建议数量")
    if payload.disposition == "partial" and payload.quantity >= advised_quantity:
        raise HTTPException(status_code=422, detail="部分执行数量必须小于建议调整数量")

    gross = _money(Decimal(payload.price) * payload.quantity)
    fee = _money(payload.fee)
    if item.action in {"buy", "increase"}:
        return payload.quantity, -(gross + fee), gross + fee
    if item.action not in {"reduce", "exit"}:
        raise HTTPException(status_code=422, detail="该建议不支持成交记录")
    if payload.quantity > base_quantity:
        raise HTTPException(status_code=422, detail="卖出数量不能超过当前持仓")
    average_cost = (
        Decimal(base_total_cost) / Decimal(base_quantity) if base_quantity else Decimal("0")
    )
    return -payload.quantity, gross - fee, -(average_cost * payload.quantity)


def _aggregate_advice_status(advice: DailyAdvice, items: list[AdviceItem]) -> str:
    if advice.status == "expired":
        return "expired"
    statuses = [item.status for item in items if item.action != "hold"]
    if statuses and all(status in HANDLED_ITEM_STATUSES for status in statuses):
        return "handled"
    if any(status != "pending" for status in statuses):
        return "partially_handled"
    return "ready"


def _is_idempotency_conflict(error: IntegrityError) -> bool:
    if not isinstance(error.orig, BaseException):
        return False

    pending: list[BaseException] = [error.orig]
    seen: set[int] = set()
    sqlstates: set[str] = set()
    target_constraint = False
    sqlite_target = False
    postgres_target_line = re.compile(
        r"^(?:(?:<class\s+[\"']asyncpg\.[^\"']*UniqueViolationError[\"']>"
        r"|asyncpg\.[\w.]*UniqueViolationError):\s*)?"
        r"duplicate key value violates unique constraint "
        r"[\"']uq_execution_mutation_key[\"']$",
        re.IGNORECASE,
    )

    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for attribute in ("sqlstate", "pgcode"):
            code = getattr(current, attribute, None)
            if code is not None:
                sqlstates.add(str(code))
        constraint = getattr(getattr(current, "diag", None), "constraint_name", None)
        if constraint == "uq_execution_mutation_key":
            target_constraint = True
        first_line = str(current).partition("\n")[0].strip()
        if postgres_target_line.fullmatch(first_line):
            target_constraint = True
        if (
            first_line.lower()
            == "unique constraint failed: execution_mutations.idempotency_key"
        ):
            sqlite_target = True
        for nested in (current.__cause__, current.__context__):
            if isinstance(nested, BaseException) and id(nested) not in seen:
                pending.append(nested)

    return sqlite_target or ("23505" in sqlstates and target_constraint)


async def update_execution(
    db: AsyncSession,
    user_id: Any,
    item_id: Any,
    payload: Any,
    idempotency_key: str,
    request_meta: tuple[str | None, str | None] | None,
) -> ExecutionResponse:
    repo = ExecutionRepository(db)
    prior_mutation = await repo.find_mutation(user_id, item_id, idempotency_key)
    if prior_mutation is not None:
        return repo.response_from_state(prior_mutation.after_state)

    locked = await repo.lock_owned_item(user_id, item_id)
    if locked is None:
        raise HTTPException(status_code=404, detail="建议项不存在")

    # A second check closes the race between the optimistic replay lookup and row lock.
    prior_mutation = await repo.find_mutation(user_id, item_id, idempotency_key)
    if prior_mutation is not None:
        return repo.response_from_state(prior_mutation.after_state)

    if locked.advice.status == "superseded" or locked.advice.superseded_by_id is not None:
        raise _conflict("advice_superseded", "该建议版本已被替代，不能再记录执行")

    current_revision = locked.record.revision if locked.record is not None else 0
    if payload.expected_revision != current_revision:
        raise _conflict("stale_execution_revision", "执行记录已更新，请刷新后重试")

    latest_market_date = await repo.latest_market_date()
    expired = locked.advice.status == "expired" or (
        latest_market_date is not None and latest_market_date > locked.advice.signal_date
    )
    traded = payload.disposition in {"executed", "partial"}
    within_price_band = True
    if traded:
        lower = Decimal(locked.item.reference_price) * (
            Decimal("1") - Decimal(locked.item.price_tolerance)
        )
        upper = Decimal(locked.item.reference_price) * (
            Decimal("1") + Decimal(locked.item.price_tolerance)
        )
        within_price_band = lower <= Decimal(payload.price) <= upper and not expired
        if not within_price_band and not payload.acknowledge_outside_advice:
            reason = "建议已过期" if expired else "成交价超出建议价格带"
            raise _conflict(
                "outside_advice_requires_acknowledgement",
                f"{reason}，确认后可仍记录为实际成交",
            )

    previous_event = None
    if locked.record is not None:
        previous_event = await repo.current_execution_event(locked.record.id)
        event_anchor = (
            previous_event.created_at if previous_event is not None else locked.record.updated_at
        )
        if await repo.has_later_symbol_event(
            portfolio_id=locked.portfolio.id,
            symbol=locked.item.symbol,
            anchor=event_anchor,
            execution_id=locked.record.id,
        ):
            raise _conflict(
                "later_symbol_event_requires_reconcile",
                "该股票已有后续组合事件，请先核对持仓后再记录",
            )

    base_cash = Decimal(locked.portfolio.cash)
    base_quantity = locked.position.quantity if locked.position is not None else 0
    base_total_cost = (
        Decimal(locked.position.total_cost) if locked.position is not None else Decimal("0")
    )
    if previous_event is not None:
        base_cash -= Decimal(previous_event.cash_delta)
        base_quantity -= previous_event.quantity_delta
        base_total_cost -= Decimal(previous_event.payload["total_cost_delta"])

    quantity_delta = 0
    cash_delta = Decimal("0")
    total_cost_delta = Decimal("0")
    if traded:
        quantity_delta, cash_delta, total_cost_delta = _trade_deltas(
            locked.item,
            payload,
            base_quantity=base_quantity,
            base_total_cost=base_total_cost,
        )
        if base_cash + cash_delta < 0:
            raise HTTPException(status_code=422, detail="现金余额不能为负数")
        if base_quantity + quantity_delta < 0:
            raise HTTPException(status_code=422, detail="卖出数量不能超过当前持仓")

    now = datetime.now(UTC)
    execution_id = locked.record.id if locked.record is not None else uuid.uuid4()
    before_state = _execution_state(
        locked.item, locked.record, locked.advice.status
    )
    await repo.create_snapshot(
        locked.portfolio,
        reason="execution_before",
        execution_id=execution_id,
        captured_at=now,
    )

    record = locked.record
    if record is None:
        record = ExecutionRecord(
            id=execution_id,
            advice_item_id=locked.item.id,
            user_id=user_id,
            disposition=payload.disposition,
            quantity=payload.quantity,
            price=_money(payload.price) if traded else None,
            fee=_money(payload.fee),
            executed_at=payload.executed_at,
            reason=payload.reason,
            within_price_band=within_price_band,
            revision=1,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
    else:
        record.disposition = payload.disposition
        record.quantity = payload.quantity
        record.price = _money(payload.price) if traded else None
        record.fee = _money(payload.fee)
        record.executed_at = payload.executed_at
        record.reason = payload.reason
        record.within_price_band = within_price_band
        record.revision += 1
        record.updated_at = now

    position = locked.position
    event_ids: list[str] = []
    if previous_event is not None:
        if position is None:
            position = Position(
                id=uuid.uuid4(),
                portfolio_id=locked.portfolio.id,
                symbol=locked.item.symbol,
                quantity=0,
                total_cost=Decimal("0"),
                created_at=now,
                updated_at=now,
            )
            db.add(position)
        reversal_cost = -Decimal(previous_event.payload["total_cost_delta"])
        locked.portfolio.cash = _money(
            Decimal(locked.portfolio.cash) - Decimal(previous_event.cash_delta)
        )
        position.quantity -= previous_event.quantity_delta
        position.total_cost = _money(Decimal(position.total_cost) + reversal_cost)
        reversal = repo.create_event(
            locked.portfolio,
            locked.item,
            record,
            event_type="advice_execution_reversal",
            quantity_delta=-previous_event.quantity_delta,
            cash_delta=-Decimal(previous_event.cash_delta),
            total_cost_delta=reversal_cost,
            occurred_at=now,
            created_at=now,
            revision=record.revision,
            reversal_of_id=previous_event.id,
        )
        event_ids.append(str(reversal.id))

    if traded:
        if position is None:
            position = Position(
                id=uuid.uuid4(),
                portfolio_id=locked.portfolio.id,
                symbol=locked.item.symbol,
                quantity=0,
                total_cost=Decimal("0"),
                created_at=now,
                updated_at=now,
            )
            db.add(position)
        locked.portfolio.cash = _money(Decimal(locked.portfolio.cash) + cash_delta)
        position.quantity += quantity_delta
        position.total_cost = _money(Decimal(position.total_cost) + total_cost_delta)
        position.updated_at = now
        event = repo.create_event(
            locked.portfolio,
            locked.item,
            record,
            event_type="advice_execution",
            quantity_delta=quantity_delta,
            cash_delta=cash_delta,
            total_cost_delta=total_cost_delta,
            occurred_at=payload.executed_at,
            created_at=now,
            revision=record.revision,
        )
        event_ids.append(str(event.id))

    if position is not None and position.quantity == 0:
        await db.delete(position)

    if expired:
        locked.advice.status = "expired"
        for advice_item in locked.advice_items:
            if advice_item.status == "pending":
                advice_item.status = "expired"
    locked.item.status = payload.disposition
    locked.advice.status = _aggregate_advice_status(locked.advice, locked.advice_items)

    await repo.create_snapshot(
        locked.portfolio,
        reason="execution_after",
        execution_id=record.id,
        captured_at=now,
    )
    response = _response(locked.item, record, locked.advice.status)
    after_state = response.model_dump(mode="json")
    mutation = ExecutionMutation(
        id=uuid.uuid4(),
        execution_id=record.id,
        idempotency_key=idempotency_key,
        revision=record.revision,
        before_state=before_state,
        after_state=after_state,
        portfolio_event_ids=event_ids,
        created_at=now,
        updated_at=now,
    )
    db.add(mutation)
    try:
        await log_action(
            db,
            user_id=user_id,
            action="advice.execution_recorded",
            resource_type="advice_item",
            resource_id=str(locked.item.id),
            detail={
                "symbols": [locked.item.symbol],
                "symbol_count": 1,
                "portfolio_event_count": len(event_ids),
            },
            **_request_metadata(request_meta),
        )
        await repo.flush()
    except IntegrityError as error:
        if _is_idempotency_conflict(error):
            raise _conflict(
                "idempotency_key_conflict",
                "该幂等键已用于其他执行请求，请更换后重试",
            ) from error
        raise
    return response
