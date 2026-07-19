from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.daily_bar import DailyBar
from app.models.investment_profile import InvestmentProfile
from app.models.portfolio import Portfolio, PortfolioEvent, PortfolioSnapshot, Position
from app.models.stock import Stock
from app.models.user import User
from app.schemas.portfolio import (
    InvestmentProfileResponse,
    PortfolioPositionResponse,
    PortfolioResponse,
    PortfolioSetupStatus,
    PortfolioSummaryResponse,
)
from app.services.audit_service import log_action

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PositionValuation:
    symbol: str
    name: str
    industry: str | None
    quantity: int
    average_cost: Decimal
    latest_close: Decimal
    price_date: date | None
    market_value: Decimal
    valuation_warning: str | None


def _profile_values(profile: Any) -> dict[str, Any]:
    return {
        "investment_horizon_days": profile.investment_horizon_days,
        "risk_level": profile.risk_level,
        "max_drawdown": profile.max_drawdown,
        "max_stock_weight": profile.max_stock_weight,
        "max_industry_weight": profile.max_industry_weight,
        "min_cash_ratio": profile.min_cash_ratio,
        "max_daily_turnover": profile.max_daily_turnover,
    }


def _profile_constraints(profile: Any) -> dict[str, Any]:
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in _profile_values(profile).items()
    }


def _request_metadata(request_meta: tuple[str | None, str | None] | None) -> dict[str, str | None]:
    ip_address, user_agent = request_meta or (None, None)
    return {"ip_address": ip_address, "user_agent": user_agent}


class PortfolioRepository:
    """User-scoped persistence operations for the portfolio aggregate."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshot_positions: list[Any] | None = None

    async def get_portfolio(self, user_id: str) -> Portfolio | None:
        result = await self.db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        return result.scalar_one_or_none()

    async def lock_user_for_setup(self, user_id: str) -> None:
        await self.db.execute(select(User.id).where(User.id == user_id).with_for_update())

    async def lock_portfolio(self, user_id: str) -> Portfolio | None:
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_positions(self, portfolio_id: str | uuid.UUID) -> list[Position]:
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        return result.scalars().all()

    async def get_active_profile(self, user_id: str) -> InvestmentProfile | None:
        result = await self.db.execute(
            select(InvestmentProfile)
            .where(
                InvestmentProfile.user_id == user_id,
                InvestmentProfile.is_active.is_(True),
            )
            .order_by(InvestmentProfile.version.desc())
        )
        return result.scalar_one_or_none()

    async def get_active_profile_for_update(self, user_id: str) -> InvestmentProfile | None:
        result = await self.db.execute(
            select(InvestmentProfile)
            .where(
                InvestmentProfile.user_id == user_id,
                InvestmentProfile.is_active.is_(True),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_profile(
        self, user_id: str, version: int, profile: Any
    ) -> InvestmentProfile:
        entity = InvestmentProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            version=version,
            is_active=True,
            **_profile_values(profile),
        )
        self.db.add(entity)
        return entity

    async def deactivate_profile(self, profile: InvestmentProfile) -> None:
        profile.is_active = False

    async def create_portfolio(self, user_id: str, cash: Decimal) -> Portfolio:
        entity = Portfolio(
            id=uuid.uuid4(),
            user_id=user_id,
            currency="CNY",
            cash=cash,
            last_confirmed_at=datetime.now(UTC),
        )
        self.db.add(entity)
        return entity

    async def replace_positions(self, portfolio_id: str | uuid.UUID, positions: list[Any]) -> None:
        await self.db.execute(delete(Position).where(Position.portfolio_id == portfolio_id))
        for item in positions:
            if item.quantity == 0:
                continue
            self.db.add(
                Position(
                    id=uuid.uuid4(),
                    portfolio_id=portfolio_id,
                    symbol=item.symbol,
                    quantity=item.quantity,
                    total_cost=item.average_cost * item.quantity,
                )
            )

    async def create_event(
        self,
        portfolio_id: str | uuid.UUID,
        *,
        event_type: str,
        symbol: str | None,
        quantity_delta: int,
        cash_delta: Decimal,
        source_type: str,
        source_id: str | None,
        payload: dict[str, Any] | None,
        occurred_at: datetime,
    ) -> PortfolioEvent:
        event = PortfolioEvent(
            id=uuid.uuid4(),
            portfolio_id=portfolio_id,
            symbol=symbol,
            event_type=event_type,
            quantity_delta=quantity_delta,
            cash_delta=cash_delta,
            source_type=source_type,
            source_id=source_id,
            payload=payload,
            occurred_at=occurred_at,
        )
        self.db.add(event)
        return event

    async def create_opening_events(
        self, portfolio_id: str | uuid.UUID, cash: Decimal, positions: list[Any]
    ) -> None:
        occurred_at = datetime.now(UTC)
        self.db.add(
            PortfolioEvent(
                id=uuid.uuid4(),
                portfolio_id=portfolio_id,
                symbol=None,
                event_type="opening_cash",
                quantity_delta=0,
                cash_delta=cash,
                source_type="setup",
                source_id=None,
                payload=None,
                occurred_at=occurred_at,
            )
        )
        for item in positions:
            if item.quantity == 0:
                continue
            self.db.add(
                PortfolioEvent(
                    id=uuid.uuid4(),
                    portfolio_id=portfolio_id,
                    symbol=item.symbol,
                    event_type="opening_position",
                    quantity_delta=item.quantity,
                    cash_delta=Decimal("0"),
                    source_type="setup",
                    source_id=None,
                    payload={"average_cost": str(item.average_cost)},
                    occurred_at=occurred_at,
                )
            )

    async def create_snapshot(
        self,
        portfolio_id: str | uuid.UUID,
        reason: str,
        reference_type: str,
        reference_id: str,
    ) -> PortfolioSnapshot:
        portfolio = next(
            (
                entity
                for entity in self.db.new
                if isinstance(entity, Portfolio) and entity.id == portfolio_id
            ),
            None,
        )
        if portfolio is None:
            result = await self.db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
            portfolio = result.scalar_one()
        positions = self.snapshot_positions
        if positions is None:
            stored_positions = await self.get_positions(portfolio_id)
            positions = [
                type("PositionValueInput", (), {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "average_cost": (
                        position.total_cost / position.quantity
                        if position.quantity
                        else Decimal("0")
                    ),
                })()
                for position in stored_positions
            ]
        valuations = await value_positions(self.db, positions)
        market_value = sum((valuation.market_value for valuation in valuations), Decimal("0"))
        warnings = [v.valuation_warning for v in valuations if v.valuation_warning]
        snapshot = PortfolioSnapshot(
            id=uuid.uuid4(),
            portfolio_id=portfolio_id,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            cash=portfolio.cash,
            market_value=market_value,
            total_asset=portfolio.cash + market_value,
            price_date=(
                None if warnings else max((v.price_date for v in valuations), default=None)
            ),
            positions=[
                {
                    "symbol": valuation.symbol,
                    "quantity": valuation.quantity,
                    "average_cost": str(valuation.average_cost),
                    "latest_close": str(valuation.latest_close),
                    "price_date": (
                        valuation.price_date.isoformat()
                        if valuation.price_date is not None
                        else None
                    ),
                    "market_value": str(valuation.market_value),
                    "valuation_warning": valuation.valuation_warning,
                }
                for valuation in valuations
            ],
            captured_at=datetime.now(UTC),
        )
        self.db.add(snapshot)
        return snapshot

    async def portfolio_response(self, user_id: str) -> PortfolioResponse:
        return await get_portfolio_response(self.db, user_id)


async def validate_symbols(db: AsyncSession, symbols: list[str]) -> None:
    if not symbols:
        return
    result = await db.execute(select(Stock).where(Stock.symbol.in_(symbols)))
    stocks = {stock.symbol: stock for stock in result.scalars().all()}
    invalid = [
        symbol for symbol in symbols if symbol not in stocks or not stocks[symbol].in_csi300
    ]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"股票不存在或不属于沪深300：{', '.join(invalid)}",
        )


async def value_positions(db: AsyncSession, positions: list[Any]) -> list[PositionValuation]:
    if not positions:
        return []
    symbols = [position.symbol for position in positions]
    stocks_result = await db.execute(select(Stock).where(Stock.symbol.in_(symbols)))
    stocks = {stock.symbol: stock for stock in stocks_result.scalars().all()}
    values: list[PositionValuation] = []
    for position in positions:
        bar_result = await db.execute(
            select(DailyBar)
            .where(DailyBar.symbol == position.symbol, DailyBar.trade_date <= date.today())
            .order_by(DailyBar.trade_date.desc())
            .limit(1)
        )
        bar = bar_result.scalar_one_or_none()
        average_cost = position.average_cost
        latest_close = bar.close if bar else average_cost
        warning = None if bar else f"{position.symbol}缺少最新行情，已按成本价估值"
        stock = stocks.get(position.symbol)
        values.append(
            PositionValuation(
                symbol=position.symbol,
                name=stock.name if stock else position.symbol,
                industry=stock.industry if stock else None,
                quantity=position.quantity,
                average_cost=average_cost,
                latest_close=latest_close,
                price_date=bar.trade_date if bar else None,
                market_value=latest_close * position.quantity,
                valuation_warning=warning,
            )
        )
    return values


async def validate_declared_capital(db: AsyncSession, payload: Any) -> None:
    valuations = await value_positions(db, payload.positions)
    server_total = payload.cash + sum(
        (valuation.market_value for valuation in valuations), Decimal("0")
    )
    tolerance = max(Decimal("100"), payload.total_capital * Decimal("0.01"))
    if abs(payload.total_capital - server_total) > tolerance:
        raise HTTPException(
            status_code=422,
            detail=f"申报总资产与服务器估值不一致，服务器估值为 {server_total}",
        )


def is_setup_duplicate_integrity_error(error: IntegrityError) -> bool:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint in {"uq_portfolio_user", "uq_investment_profile_user_version"}:
        return True
    message = str(error.orig).lower()
    return any(
        marker in message
        for marker in (
            "unique constraint failed: portfolios.user_id",
            "unique constraint failed: investment_profiles.user_id, investment_profiles.version",
        )
    )


async def get_setup_status(db: AsyncSession, user_id: str) -> PortfolioSetupStatus:
    repo = PortfolioRepository(db)
    profile = await repo.get_active_profile(user_id)
    portfolio = await repo.get_portfolio(user_id)
    return PortfolioSetupStatus(
        has_profile=profile is not None,
        has_portfolio=portfolio is not None,
    )


async def complete_setup(
    db: AsyncSession, user_id: str, payload: Any, request_meta: Any
) -> PortfolioResponse:
    repo = PortfolioRepository(db)
    await repo.lock_user_for_setup(user_id)
    if await repo.get_portfolio(user_id):
        raise HTTPException(status_code=409, detail="投资组合已经初始化")
    await validate_symbols(db, [item.symbol for item in payload.positions])
    await validate_declared_capital(db, payload)
    try:
        profile = await repo.create_profile(user_id, 1, payload.profile)
        portfolio = await repo.create_portfolio(user_id, payload.cash)
        repo.snapshot_positions = payload.positions
        await repo.replace_positions(portfolio.id, payload.positions)
        await repo.create_opening_events(portfolio.id, payload.cash, payload.positions)
        await repo.create_snapshot(portfolio.id, "setup", "profile", str(profile.id))
        await log_action(
            db,
            user_id=user_id,
            action="portfolio.setup",
            resource_type="portfolio",
            resource_id=str(portfolio.id),
            detail={"positions": len(payload.positions)},
            **_request_metadata(request_meta),
        )
        await db.flush()
        return await repo.portfolio_response(user_id)
    except IntegrityError as error:
        if is_setup_duplicate_integrity_error(error):
            raise HTTPException(status_code=409, detail="投资组合已经初始化") from error
        raise


async def create_profile_version(
    db: AsyncSession, user_id: str, payload: Any, request_meta: Any
) -> InvestmentProfileResponse:
    repo = PortfolioRepository(db)
    active = await repo.get_active_profile_for_update(user_id)
    if active is None:
        raise HTTPException(status_code=409, detail="投资者画像尚未初始化")
    await repo.deactivate_profile(active)
    profile = await repo.create_profile(user_id, active.version + 1, payload)
    await log_action(
        db,
        user_id=user_id,
        action="portfolio.profile_version_created",
        resource_type="investment_profile",
        resource_id=str(profile.id),
        detail={
            "old": _profile_constraints(active),
            "new": _profile_constraints(payload),
            "version": profile.version,
        },
        **_request_metadata(request_meta),
    )
    await db.flush()
    if isinstance(profile, InvestmentProfile):
        return InvestmentProfileResponse.model_validate(profile)
    return profile


def _position_state(positions: list[Any]) -> list[dict[str, Any]]:
    state: list[dict[str, Any]] = []
    for position in positions:
        if position.quantity == 0:
            continue
        average_cost = getattr(position, "average_cost", None)
        if average_cost is None:
            average_cost = position.total_cost / position.quantity
        state.append(
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "average_cost": str(average_cost),
            }
        )
    return state


async def reconcile_holdings(
    db: AsyncSession, user_id: str, payload: Any, request_meta: Any
) -> PortfolioResponse:
    repo = PortfolioRepository(db)
    portfolio = await repo.lock_portfolio(user_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="投资组合尚未初始化")
    if portfolio.updated_at != payload.expected_updated_at:
        raise HTTPException(status_code=409, detail="投资组合已更新，请刷新后重试")

    await validate_symbols(db, [item.symbol for item in payload.positions])
    before_positions = await repo.get_positions(portfolio.id)
    before_state = _position_state(before_positions)
    after_state = _position_state(payload.positions)
    occurred_at = datetime.now(UTC)

    repo.snapshot_positions = before_positions
    await repo.create_snapshot(portfolio.id, "before_reconcile", "portfolio", str(portfolio.id))
    await repo.replace_positions(portfolio.id, payload.positions)
    before_cash = portfolio.cash
    portfolio.cash = payload.cash
    portfolio.last_confirmed_at = occurred_at
    event = await repo.create_event(
        portfolio.id,
        event_type="reconcile",
        symbol=None,
        quantity_delta=0,
        cash_delta=payload.cash - before_cash,
        source_type="manual",
        source_id=None,
        payload={
            "before": {"cash": str(before_cash), "positions": before_state},
            "after": {"cash": str(payload.cash), "positions": after_state},
        },
        occurred_at=occurred_at,
    )
    repo.snapshot_positions = payload.positions
    await repo.create_snapshot(portfolio.id, "after_reconcile", "portfolio_event", str(event.id))
    changed_symbols = {
        item["symbol"]
        for item in before_state + after_state
        if next((other for other in before_state if other["symbol"] == item["symbol"]), None)
        != next((other for other in after_state if other["symbol"] == item["symbol"]), None)
    }
    await log_action(
        db,
        user_id=user_id,
        action="portfolio.holdings_reconciled",
        resource_type="portfolio",
        resource_id=str(portfolio.id),
        detail={
            "before_position_count": len(before_state),
            "after_position_count": len(after_state),
            "changed_symbol_count": len(changed_symbols),
        },
        **_request_metadata(request_meta),
    )
    await db.flush()
    return await repo.portfolio_response(user_id)


async def record_cash_movement(
    db: AsyncSession, user_id: str, payload: Any, request_meta: Any
) -> PortfolioResponse:
    repo = PortfolioRepository(db)
    portfolio = await repo.lock_portfolio(user_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="投资组合尚未初始化")

    cash_delta = payload.amount if payload.kind == "deposit" else -payload.amount
    if portfolio.cash + cash_delta < 0:
        raise HTTPException(status_code=422, detail="现金余额不能为负数")

    event = await repo.create_event(
        portfolio.id,
        event_type=f"cash_{payload.kind}",
        symbol=None,
        quantity_delta=0,
        cash_delta=cash_delta,
        source_type="manual",
        source_id=None,
        payload={"note": payload.note},
        occurred_at=payload.occurred_at,
    )
    portfolio.cash += cash_delta
    await repo.create_snapshot(portfolio.id, "cash_movement", "portfolio_event", str(event.id))
    await log_action(
        db,
        user_id=user_id,
        action="portfolio.cash_movement_recorded",
        resource_type="portfolio",
        resource_id=str(portfolio.id),
        detail={"kind": payload.kind},
        **_request_metadata(request_meta),
    )
    await db.flush()
    return await repo.portfolio_response(user_id)


async def get_portfolio_response(db: AsyncSession, user_id: str) -> PortfolioResponse:
    repo = PortfolioRepository(db)
    profile = await repo.get_active_profile(user_id)
    portfolio = await repo.get_portfolio(user_id)
    if profile is None or portfolio is None:
        raise HTTPException(status_code=404, detail="投资组合尚未初始化")
    position_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    stored_positions = position_result.scalars().all()
    inputs = [
        type("PositionValueInput", (), {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_cost": (
                position.total_cost / position.quantity
                if position.quantity
                else Decimal("0")
            ),
        })()
        for position in stored_positions
    ]
    valuations = await value_positions(db, inputs)
    market_value = sum((valuation.market_value for valuation in valuations), Decimal("0"))
    total_asset = portfolio.cash + market_value
    warnings = [
        valuation.valuation_warning for valuation in valuations if valuation.valuation_warning
    ]
    response_positions = [
        PortfolioPositionResponse(
            id=position.id,
            symbol=valuation.symbol,
            name=valuation.name,
            industry=valuation.industry,
            quantity=valuation.quantity,
            average_cost=valuation.average_cost,
            latest_close=valuation.latest_close,
            price_date=valuation.price_date,
            market_value=valuation.market_value,
            unrealized_pnl=valuation.market_value - (valuation.average_cost * valuation.quantity),
            current_weight=(valuation.market_value / total_asset if total_asset else Decimal("0")),
            valuation_warning=valuation.valuation_warning,
        )
        for position, valuation in zip(stored_positions, valuations, strict=True)
    ]
    return PortfolioResponse(
        profile=InvestmentProfileResponse.model_validate(profile),
        summary=PortfolioSummaryResponse(
            id=portfolio.id,
            currency=portfolio.currency,
            cash=portfolio.cash,
            market_value=market_value,
            total_asset=total_asset,
            exposure=(market_value / total_asset if total_asset else Decimal("0")),
            valuation_date=(
                None if warnings else max((v.price_date for v in valuations), default=None)
            ),
            last_confirmed_at=portfolio.last_confirmed_at,
            updated_at=portfolio.updated_at,
        ),
        positions=response_positions,
        valuation_warnings=warnings,
        updated_at=portfolio.updated_at,
    )
