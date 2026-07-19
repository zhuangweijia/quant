from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.database import AsyncSessionLocal
from app.models.advice import AdviceItem, DailyAdvice
from app.models.daily_bar import DailyBar
from app.models.execution import ExecutionRecord
from app.models.investment_profile import InvestmentProfile
from app.models.portfolio import Portfolio, PortfolioSnapshot, Position
from app.models.prediction import Prediction
from app.models.stock import Stock
from app.models.user import User
from app.schemas.advice import (
    AdviceItemResponse,
    AdviceTodayResponse,
    DailyAdviceResponse,
    ExecutionRecordResponse,
)
from app.services.advice_engine import (
    EngineCandidate,
    EnginePosition,
    EngineProfile,
    EngineResult,
    build_advice,
)

logger = structlog.get_logger()

PRICE_TOLERANCE = Decimal("0.03")
ESTIMATED_COST_RATE = Decimal("0.001")
MAX_RETURN_SESSIONS = 120
UNRESOLVED_STATUSES = {"generating", "ready", "partially_handled"}
SUCCESS_STATUSES = {"ready", "partially_handled", "handled", "expired"}
MISSING_HELD_QUOTE_WARNING = "缺少信号日收盘价，失败快照按录入平均成本估值"

ERROR_MESSAGES = {
    "candidate_market_data_missing": "候选股票行情数据不完整",
    "engine_failed": "建议生成失败，请稍后重试",
    "held_market_data_missing": "持仓股票缺少当日行情，无法生成精确数量建议",
    "holdings_stale": "上期建议尚未确认，当前持仓可能已过期，请先核对持仓",
    "market_history_incomplete": "候选股票历史行情不足",
    "mixed_model_versions": "当日排名包含多个模型版本",
    "portfolio_setup_required": "请先完成投资画像和组合设置",
    "ranked_predictions_missing": "暂无可用的当日排名，请等待分析完成后再生成建议",
}


class AdviceInputError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AdviceInputs:
    user_id: Any
    profile: Any
    portfolio: Any
    positions: tuple[Any, ...]
    engine_profile: Any
    engine_positions: tuple[EnginePosition, ...]
    engine_candidates: tuple[EngineCandidate, ...]
    snapshot_positions: tuple[dict[str, Any], ...]
    model_version: str
    data_date: date
    input_error_code: str | None = None


def _failure_detail(code: str) -> dict[str, str]:
    return {"code": code, "message": ERROR_MESSAGES[code]}


def _common_returns(
    history_rows: list[Any], candidate_symbols: tuple[str, ...]
) -> dict[str, tuple[float, ...]]:
    closes: dict[str, dict[date, Decimal]] = {symbol: {} for symbol in candidate_symbols}
    for symbol, trade_date, close in history_rows:
        if symbol in closes:
            closes[symbol][trade_date] = Decimal(close)
    if not candidate_symbols:
        return {}
    common_dates = set(closes[candidate_symbols[0]])
    for symbol in candidate_symbols[1:]:
        common_dates.intersection_update(closes[symbol])
    ordered_dates = sorted(common_dates)[-(MAX_RETURN_SESSIONS + 1) :]
    returns: dict[str, tuple[float, ...]] = {}
    for symbol in candidate_symbols:
        series: list[float] = []
        for previous_date, current_date in zip(ordered_dates, ordered_dates[1:]):
            previous = closes[symbol][previous_date]
            current = closes[symbol][current_date]
            if previous <= 0:
                raise AdviceInputError("market_history_incomplete")
            series.append(float(current / previous - Decimal("1")))
        returns[symbol] = tuple(series)
    return returns


def _snapshot_position(
    position: Any, stock: Any | None, bar: Any | None, signal_date: date
) -> dict[str, Any]:
    average_cost = (
        Decimal(position.total_cost) / Decimal(position.quantity)
        if position.quantity
        else Decimal("0")
    )
    latest_close = Decimal(bar.close) if bar is not None else None
    valuation_price = latest_close if latest_close is not None else average_cost
    if latest_close is None:
        warning = MISSING_HELD_QUOTE_WARNING
    elif stock is None:
        warning = "股票资料缺失"
    else:
        warning = None
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "average_cost": str(average_cost),
        "latest_close": str(latest_close) if latest_close is not None else None,
        "price_date": signal_date.isoformat() if latest_close is not None else None,
        "market_value": str(Decimal(position.quantity) * valuation_price),
        "valuation_warning": warning,
    }


class AdviceRepository:
    """Batched, user-scoped persistence for immutable daily advice."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_current(self, user_id: Any, signal_date: date | None = None):
        query = select(DailyAdvice).where(
            DailyAdvice.user_id == user_id,
            DailyAdvice.status.not_in(("failed", "superseded")),
            DailyAdvice.superseded_by_id.is_(None),
        )
        if signal_date is not None:
            query = query.where(DailyAdvice.signal_date == signal_date)
        result = await self.db.execute(
            query.order_by(DailyAdvice.signal_date.desc(), DailyAdvice.version.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def find_latest(self, user_id: Any):
        result = await self.db.execute(
            select(DailyAdvice)
            .where(
                DailyAdvice.user_id == user_id,
                DailyAdvice.status != "superseded",
                DailyAdvice.superseded_by_id.is_(None),
            )
            .order_by(DailyAdvice.signal_date.desc(), DailyAdvice.version.desc())
        )
        rows = result.scalars().all()
        if not rows:
            return None
        newest_date = rows[0].signal_date
        same_date = [row for row in rows if row.signal_date == newest_date]
        return next((row for row in same_date if row.status != "failed"), same_date[0])

    async def lock_versions(self, user_id: Any, signal_date: date) -> list[DailyAdvice]:
        await self.db.execute(select(User.id).where(User.id == user_id).with_for_update())
        result = await self.db.execute(
            select(DailyAdvice)
            .where(
                DailyAdvice.user_id == user_id,
                DailyAdvice.signal_date == signal_date,
            )
            .order_by(DailyAdvice.version)
            .with_for_update()
        )
        return result.scalars().all()

    async def load_inputs(self, user_id: Any, signal_date: date) -> AdviceInputs | None:
        profile_result = await self.db.execute(
            select(InvestmentProfile)
            .where(
                InvestmentProfile.user_id == user_id,
                InvestmentProfile.is_active.is_(True),
            )
            .order_by(InvestmentProfile.version.desc())
        )
        profile = profile_result.scalar_one_or_none()
        portfolio_result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        if profile is None or portfolio is None:
            return None

        positions_result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .order_by(Position.symbol)
        )
        positions = tuple(positions_result.scalars().all())
        predictions_result = await self.db.execute(
            select(Prediction)
            .where(
                Prediction.trade_date == signal_date,
                Prediction.rank.is_not(None),
            )
            .order_by(Prediction.rank, Prediction.symbol)
        )
        predictions = tuple(predictions_result.scalars().all())
        if not predictions:
            raise AdviceInputError("ranked_predictions_missing")
        model_versions = {prediction.model_version for prediction in predictions}
        if len(model_versions) != 1:
            raise AdviceInputError("mixed_model_versions")

        held_symbols = {position.symbol for position in positions}
        candidate_symbols = tuple(prediction.symbol for prediction in predictions)
        symbols = tuple(sorted(held_symbols | set(candidate_symbols)))
        stocks_result = await self.db.execute(
            select(Stock).where(
                Stock.symbol.in_(symbols),
                Stock.in_csi300.is_(True),
            )
        )
        stocks = {stock.symbol: stock for stock in stocks_result.scalars().all()}
        bars_result = await self.db.execute(
            select(DailyBar).where(
                DailyBar.symbol.in_(symbols), DailyBar.trade_date == signal_date
            )
        )
        same_date_bars = {bar.symbol: bar for bar in bars_result.scalars().all()}

        returns_by_symbol = await self.load_common_returns(candidate_symbols, signal_date)

        missing_held = held_symbols - (set(stocks) & set(same_date_bars))
        missing_candidates = set(candidate_symbols) - (set(stocks) & set(same_date_bars))
        input_error_code = None
        if missing_held:
            input_error_code = "held_market_data_missing"
        elif missing_candidates:
            input_error_code = "candidate_market_data_missing"

        engine_positions: list[EnginePosition] = []
        snapshot_positions: list[dict[str, Any]] = []
        for position in positions:
            stock = stocks.get(position.symbol)
            bar = same_date_bars.get(position.symbol)
            price = Decimal(bar.close) if bar is not None else None
            snapshot_position = _snapshot_position(position, stock, bar, signal_date)
            snapshot_positions.append(snapshot_position)
            if stock is not None and price is not None:
                engine_positions.append(
                    EnginePosition(
                        position.symbol,
                        stock.name,
                        stock.industry,
                        position.quantity,
                        price,
                        Decimal(snapshot_position["market_value"]),
                    )
                )

        engine_candidates: list[EngineCandidate] = []
        for prediction in predictions:
            stock = stocks.get(prediction.symbol)
            bar = same_date_bars.get(prediction.symbol)
            if stock is None or bar is None:
                continue
            explanation = prediction.explanation or {}
            engine_candidates.append(
                EngineCandidate(
                    symbol=prediction.symbol,
                    name=stock.name,
                    industry=stock.industry,
                    score=Decimal(prediction.score),
                    rank=prediction.rank,
                    confidence=prediction.confidence,
                    price=Decimal(bar.close),
                    returns=returns_by_symbol.get(prediction.symbol, ()),
                    positive_factors=tuple(explanation.get("positive") or ()),
                    risks=tuple(explanation.get("negative") or ()),
                )
            )

        if input_error_code is None:
            new_symbols = set(candidate_symbols) - held_symbols
            if any(len(returns_by_symbol.get(symbol, ())) < 60 for symbol in new_symbols):
                input_error_code = "market_history_incomplete"

        return AdviceInputs(
            user_id=user_id,
            profile=profile,
            portfolio=portfolio,
            positions=positions,
            engine_profile=EngineProfile(
                max_drawdown=Decimal(profile.max_drawdown),
                max_stock_weight=Decimal(profile.max_stock_weight),
                max_industry_weight=Decimal(profile.max_industry_weight),
                min_cash_ratio=Decimal(profile.min_cash_ratio),
                max_daily_turnover=Decimal(profile.max_daily_turnover),
                price_tolerance=PRICE_TOLERANCE,
            ),
            engine_positions=tuple(engine_positions),
            engine_candidates=tuple(engine_candidates),
            snapshot_positions=tuple(snapshot_positions),
            model_version=next(iter(model_versions)),
            data_date=signal_date,
            input_error_code=input_error_code,
        )

    async def load_common_returns(
        self, candidate_symbols: tuple[str, ...], signal_date: date
    ) -> dict[str, tuple[float, ...]]:
        symbols = tuple(sorted(set(candidate_symbols)))
        if not symbols:
            return {}
        common_dates_result = await self.db.execute(
            select(DailyBar.trade_date)
            .where(
                DailyBar.symbol.in_(symbols),
                DailyBar.trade_date <= signal_date,
            )
            .group_by(DailyBar.trade_date)
            .having(func.count(func.distinct(DailyBar.symbol)) == len(symbols))
            .order_by(DailyBar.trade_date.desc())
            .limit(MAX_RETURN_SESSIONS + 1)
        )
        common_dates = tuple(common_dates_result.scalars().all())
        history_result = await self.db.execute(
            select(DailyBar.symbol, DailyBar.trade_date, DailyBar.close)
            .where(
                DailyBar.symbol.in_(symbols),
                DailyBar.trade_date.in_(common_dates),
            )
            .order_by(DailyBar.trade_date, DailyBar.symbol)
        )
        return _common_returns(history_result.all(), symbols)

    async def holdings_are_stale(self, user_id: Any, signal_date: date) -> bool:
        pending = await self.db.scalar(
            select(func.count(AdviceItem.id))
            .join(DailyAdvice, DailyAdvice.id == AdviceItem.advice_id)
            .where(
                DailyAdvice.user_id == user_id,
                DailyAdvice.signal_date < signal_date,
                DailyAdvice.status.in_(("ready", "partially_handled")),
                AdviceItem.status == "pending",
            )
        )
        return bool(pending)

    async def create_snapshot(self, inputs: AdviceInputs) -> PortfolioSnapshot:
        market_value = sum(
            (Decimal(position["market_value"]) for position in inputs.snapshot_positions),
            Decimal("0"),
        )
        warnings = [
            position["valuation_warning"]
            for position in inputs.snapshot_positions
            if position["valuation_warning"]
        ]
        snapshot = PortfolioSnapshot(
            id=uuid.uuid4(),
            portfolio_id=inputs.portfolio.id,
            reason="advice_generation",
            reference_type="daily_advice",
            reference_id=f"{inputs.user_id}:{inputs.data_date.isoformat()}",
            cash=inputs.portfolio.cash,
            market_value=market_value,
            total_asset=Decimal(inputs.portfolio.cash) + market_value,
            price_date=None if warnings else inputs.data_date,
            positions=list(inputs.snapshot_positions),
            captured_at=datetime.now(UTC),
        )
        self.db.add(snapshot)
        return snapshot

    async def persist_result(
        self,
        inputs: AdviceInputs,
        snapshot: PortfolioSnapshot,
        *,
        signal_date: date,
        version: int,
        result: EngineResult,
    ) -> DailyAdvice:
        advice = DailyAdvice(
            id=uuid.uuid4(),
            user_id=inputs.user_id,
            portfolio_id=inputs.portfolio.id,
            profile_id=inputs.profile.id,
            source_snapshot_id=snapshot.id,
            signal_date=signal_date,
            version=version,
            status="ready",
            model_version=inputs.model_version,
            data_date=inputs.data_date,
            current_exposure=result.current_exposure,
            target_exposure=result.target_exposure,
            estimated_cash=result.estimated_cash,
            constraint_violations=list(result.constraint_violations),
            generated_at=datetime.now(UTC),
        )
        self.db.add(advice)
        for line in result.lines:
            tolerance = format(line.price_tolerance * Decimal("100"), "f").rstrip("0").rstrip(".")
            self.db.add(
                AdviceItem(
                    id=uuid.uuid4(),
                    advice_id=advice.id,
                    symbol=line.symbol,
                    name=line.name,
                    industry=line.industry,
                    action=line.action,
                    status="pending",
                    current_quantity=line.current_quantity,
                    target_quantity=line.target_quantity,
                    delta_quantity=line.delta_quantity,
                    current_weight=line.current_weight,
                    target_weight=line.target_weight,
                    reference_price=line.reference_price,
                    price_tolerance=line.price_tolerance,
                    score=line.score,
                    rank=line.rank,
                    confidence=line.confidence,
                    positive_factors=list(line.positive_factors),
                    risks=list(line.risks),
                    invalidation_conditions=[
                        f"成交价偏离参考价超过±{tolerance}%",
                        "模型或行情数据更新后建议失效",
                        "出现更新交易日后未处理建议自动过期",
                    ],
                    constraint_notes=list(line.constraint_notes),
                )
            )
        return advice

    async def persist_failure(
        self,
        inputs: AdviceInputs,
        snapshot: PortfolioSnapshot,
        *,
        signal_date: date,
        version: int,
        error_code: str,
    ) -> DailyAdvice:
        current_exposure = (
            snapshot.market_value / snapshot.total_asset
            if snapshot.total_asset
            else Decimal("0")
        )
        advice = DailyAdvice(
            id=uuid.uuid4(),
            user_id=inputs.user_id,
            portfolio_id=inputs.portfolio.id,
            profile_id=inputs.profile.id,
            source_snapshot_id=snapshot.id,
            signal_date=signal_date,
            version=version,
            status="failed",
            model_version=inputs.model_version,
            data_date=inputs.data_date,
            current_exposure=current_exposure,
            target_exposure=current_exposure,
            estimated_cash=snapshot.cash,
            constraint_violations=[],
            generated_at=datetime.now(UTC),
            error_code=error_code,
            error_message=ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["engine_failed"]),
        )
        self.db.add(advice)
        return advice

    async def flush(self) -> None:
        await self.db.flush()

    async def supersede(self, prior: DailyAdvice, replacement: DailyAdvice) -> None:
        prior.status = "superseded"
        prior.superseded_by_id = replacement.id

    async def latest_market_date(self) -> date | None:
        return await self.db.scalar(select(func.max(DailyBar.trade_date)))

    async def find_expirable(self, user_id: Any, latest_market_date: date) -> list[DailyAdvice]:
        result = await self.db.execute(
            select(DailyAdvice)
            .where(
                DailyAdvice.user_id == user_id,
                DailyAdvice.signal_date < latest_market_date,
                DailyAdvice.status.in_(tuple(sorted(UNRESOLVED_STATUSES))),
                DailyAdvice.superseded_by_id.is_(None),
            )
            .order_by(DailyAdvice.signal_date, DailyAdvice.version)
        )
        return list(result.scalars().all())

    async def expire(self, advice: DailyAdvice) -> None:
        advice.status = "expired"
        await self.db.execute(
            update(AdviceItem)
            .where(AdviceItem.advice_id == advice.id, AdviceItem.status == "pending")
            .values(status="expired")
        )

    async def count_items(self, advice_id: Any) -> int:
        return int(
            await self.db.scalar(
                select(func.count(AdviceItem.id)).where(AdviceItem.advice_id == advice_id)
            )
            or 0
        )

    async def setup_complete(self, user_id: Any) -> bool:
        profile_count = await self.db.scalar(
            select(func.count(InvestmentProfile.id)).where(
                InvestmentProfile.user_id == user_id,
                InvestmentProfile.is_active.is_(True),
            )
        )
        portfolio_count = await self.db.scalar(
            select(func.count(Portfolio.id)).where(Portfolio.user_id == user_id)
        )
        return bool(profile_count and portfolio_count)

    async def to_response(self, advice: DailyAdvice) -> DailyAdviceResponse:
        snapshot = await self.db.scalar(
            select(PortfolioSnapshot).where(PortfolioSnapshot.id == advice.source_snapshot_id)
        )
        portfolio = await self.db.scalar(
            select(Portfolio).where(
                Portfolio.id == advice.portfolio_id,
                Portfolio.user_id == advice.user_id,
            )
        )
        rows = (
            await self.db.execute(
                select(AdviceItem, ExecutionRecord)
                .outerjoin(ExecutionRecord, ExecutionRecord.advice_item_id == AdviceItem.id)
                .where(AdviceItem.advice_id == advice.id)
                .order_by(AdviceItem.created_at, AdviceItem.symbol)
            )
        ).all()
        item_statuses = [item.status for item, _execution in rows]
        response_status = advice.status
        if advice.status in {"ready", "partially_handled", "handled"} and item_statuses:
            handled = {"executed", "skipped", "expired"}
            if all(status in handled for status in item_statuses):
                response_status = "handled"
            elif any(status != "pending" for status in item_statuses):
                response_status = "partially_handled"
            else:
                response_status = "ready"
            advice.status = response_status
        snapshot_by_symbol = {
            position["symbol"]: position for position in (snapshot.positions if snapshot else [])
        }
        item_responses = []
        for item, execution in rows:
            snapshot_position = snapshot_by_symbol.get(item.symbol, {})
            execution_response = None
            if execution is not None:
                execution_response = ExecutionRecordResponse(
                    id=execution.id,
                    disposition=execution.disposition,
                    quantity=execution.quantity,
                    price=execution.price,
                    fee=execution.fee,
                    executed_at=execution.executed_at,
                    reason=execution.reason or "",
                    within_price_band=execution.within_price_band,
                    revision=execution.revision,
                    created_at=execution.created_at,
                    updated_at=execution.updated_at,
                )
            item_responses.append(
                AdviceItemResponse(
                    id=item.id,
                    symbol=item.symbol,
                    name=item.name,
                    industry=item.industry,
                    action=item.action,
                    status=item.status,
                    current_quantity=item.current_quantity,
                    target_quantity=item.target_quantity,
                    delta_quantity=item.delta_quantity,
                    current_average_cost=snapshot_position.get("average_cost"),
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
                    execution=execution_response,
                )
            )
        warnings = sorted(
            {
                position["valuation_warning"]
                for position in (snapshot.positions if snapshot else [])
                if position.get("valuation_warning")
            }
        )
        return DailyAdviceResponse(
            id=advice.id,
            signal_date=advice.signal_date,
            version=advice.version,
            status=response_status,
            model_version=advice.model_version,
            data_date=advice.data_date,
            current_exposure=advice.current_exposure,
            target_exposure=advice.target_exposure,
            current_cash=snapshot.cash,
            estimated_cash=advice.estimated_cash,
            total_asset=snapshot.total_asset,
            generated_at=advice.generated_at,
            portfolio_updated_at=portfolio.updated_at,
            stale_warnings=warnings,
            constraint_violations=list(advice.constraint_violations),
            items=item_responses,
            error_code=advice.error_code,
            error_message=advice.error_message,
        )


async def generate_for_user(
    db: AsyncSession,
    user_id: Any,
    signal_date: date,
    force: bool = False,
) -> DailyAdvice:
    repo = AdviceRepository(db)
    existing = await repo.find_current(user_id, signal_date)
    if existing is not None and not force:
        return existing

    versions = await repo.lock_versions(user_id, signal_date)
    current = next(
        (
            advice
            for advice in reversed(versions)
            if advice.status not in {"failed", "superseded"}
            and getattr(advice, "superseded_by_id", None) is None
        ),
        None,
    )
    if current is not None and not force:
        return current
    version = max((advice.version for advice in versions), default=0) + 1

    try:
        inputs = await repo.load_inputs(user_id, signal_date)
    except AdviceInputError as exc:
        raise HTTPException(status_code=409, detail=_failure_detail(exc.code)) from exc
    if inputs is None:
        raise HTTPException(
            status_code=409, detail=_failure_detail("portfolio_setup_required")
        )

    snapshot = await repo.create_snapshot(inputs)
    failure_code = inputs.input_error_code
    if failure_code is None and await repo.holdings_are_stale(user_id, signal_date):
        failure_code = "holdings_stale"
    if failure_code is not None:
        failed = await repo.persist_failure(
            inputs,
            snapshot,
            signal_date=signal_date,
            version=version,
            error_code=failure_code,
        )
        await repo.flush()
        return failed

    try:
        result = build_advice(
            inputs.engine_profile,
            Decimal(inputs.portfolio.cash),
            inputs.engine_positions,
            inputs.engine_candidates,
            ESTIMATED_COST_RATE,
        )
    except ValueError:
        failed = await repo.persist_failure(
            inputs,
            snapshot,
            signal_date=signal_date,
            version=version,
            error_code="engine_failed",
        )
        await repo.flush()
        return failed

    advice = await repo.persist_result(
        inputs,
        snapshot,
        signal_date=signal_date,
        version=version,
        result=result,
    )
    await repo.flush()
    if current is not None:
        await repo.supersede(current, advice)
    return advice


async def expire_if_needed(db: AsyncSession, advice: DailyAdvice) -> None:
    if advice.status not in UNRESOLVED_STATUSES:
        return
    repo = AdviceRepository(db)
    latest = await repo.latest_market_date()
    if latest is not None and latest > advice.signal_date:
        await repo.expire(advice)


async def expire_stale_advice(db: AsyncSession, user_id: Any) -> None:
    repo = AdviceRepository(db)
    latest = await repo.latest_market_date()
    if latest is None:
        return
    for advice in await repo.find_expirable(user_id, latest):
        await repo.expire(advice)


async def get_advice_response(
    db: AsyncSession, advice: DailyAdvice
) -> DailyAdviceResponse:
    return await AdviceRepository(db).to_response(advice)


async def get_today_state(db: AsyncSession, user_id: Any) -> AdviceTodayResponse:
    await expire_stale_advice(db, user_id)
    repo = AdviceRepository(db)
    advice = await repo.find_latest(user_id)
    if advice is None:
        complete = await repo.setup_complete(user_id)
        return AdviceTodayResponse(
            state="not_generated",
            setup_required=not complete,
            error_code=None if complete else "portfolio_setup_required",
            error_message=None if complete else ERROR_MESSAGES["portfolio_setup_required"],
        )
    response = await repo.to_response(advice)
    return AdviceTodayResponse(
        state=response.status,
        advice=response,
        error_code=advice.error_code,
        error_message=advice.error_message,
    )


async def latest_ranked_signal_date(db: AsyncSession) -> date | None:
    return await db.scalar(
        select(func.max(Prediction.trade_date)).where(Prediction.rank.is_not(None))
    )


async def _list_active_user_ids() -> list[Any]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.id).where(User.is_active.is_(True)).order_by(User.id)
        )
        return list(result.scalars().all())


async def _generate_and_publish(user_id: Any, signal_date: date) -> DailyAdvice:
    async with AsyncSessionLocal() as db:
        try:
            advice = await generate_for_user(db, user_id, signal_date)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    if advice.status not in SUCCESS_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": advice.error_code or "engine_failed",
                "message": advice.error_message or ERROR_MESSAGES["engine_failed"],
            },
        )
    await event_bus.publish(
        event_bus.TOPIC_ADVICE_READY,
        {
            "user_id": str(user_id),
            "advice_id": str(advice.id),
            "signal_date": signal_date.isoformat(),
        },
    )
    return advice


async def generate_for_all_users(signal_date: date) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "signal_date": signal_date.isoformat(),
        "succeeded": [],
        "failed": [],
    }
    for user_id in await _list_active_user_ids():
        try:
            advice = await _generate_and_publish(user_id, signal_date)
            summary["succeeded"].append(
                {"user_id": str(user_id), "advice_id": str(advice.id)}
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            error_code = detail.get("code", "generation_failed")
            summary["failed"].append(
                {"user_id": str(user_id), "error_code": error_code}
            )
            logger.warning(
                "portfolio_advice.user_failed", user_id=str(user_id), error_code=error_code
            )
        except Exception:
            summary["failed"].append(
                {"user_id": str(user_id), "error_code": "generation_failed"}
            )
            logger.exception("portfolio_advice.user_failed", user_id=str(user_id))
    return summary
