"""Pure, deterministic constrained portfolio advice calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from statistics import pstdev
from typing import Literal

ZERO = Decimal("0")
ONE = Decimal("1")
LOT_SIZE = 100
MIN_VOLATILITY = Decimal("0.005")
MAX_RETURN_SESSIONS = 120
ACTION_PRIORITY = {"exit": 0, "reduce": 1, "buy": 2, "increase": 3, "hold": 4}

AdviceAction = Literal["exit", "reduce", "buy", "increase", "hold"]


@dataclass(frozen=True)
class EngineProfile:
    max_drawdown: Decimal
    max_stock_weight: Decimal
    max_industry_weight: Decimal
    min_cash_ratio: Decimal
    max_daily_turnover: Decimal
    price_tolerance: Decimal


@dataclass(frozen=True)
class EnginePosition:
    symbol: str
    name: str
    industry: str | None
    quantity: int
    price: Decimal | None
    market_value: Decimal


@dataclass(frozen=True)
class EngineCandidate:
    symbol: str
    name: str
    industry: str | None
    score: Decimal
    rank: int
    confidence: str
    price: Decimal
    returns: tuple[float, ...]
    positive_factors: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class EngineLine:
    symbol: str
    name: str
    industry: str | None
    action: AdviceAction
    current_quantity: int
    target_quantity: int
    delta_quantity: int
    current_weight: Decimal
    target_weight: Decimal
    reference_price: Decimal
    price_tolerance: Decimal
    score: Decimal
    rank: int | None
    confidence: str
    positive_factors: tuple[str, ...]
    risks: tuple[str, ...]
    constraint_notes: tuple[str, ...]


@dataclass(frozen=True)
class EngineResult:
    current_exposure: Decimal
    target_exposure: Decimal
    estimated_cash: Decimal
    total_asset: Decimal
    historical_max_drawdown: Decimal
    turnover: Decimal
    constraint_violations: tuple[str, ...]
    lines: tuple[EngineLine, ...]


def historical_max_drawdown(returns: tuple[float, ...]) -> Decimal:
    """Return the observed peak-to-trough drawdown for a return series."""
    value = peak = 1.0
    worst = 0.0
    for daily_return in returns:
        value *= 1.0 + daily_return
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return Decimal(str(worst))


def _validate_inputs(
    cash: Decimal,
    positions: tuple[EnginePosition, ...],
    candidates: tuple[EngineCandidate, ...],
    estimated_cost_rate: Decimal,
) -> None:
    if cash <= ZERO:
        raise ValueError("cash must be positive")
    if estimated_cost_rate < ZERO:
        raise ValueError("estimated cost rate must not be negative")

    position_symbols = [position.symbol for position in positions]
    candidate_symbols = [candidate.symbol for candidate in candidates]
    if len(position_symbols) != len(set(position_symbols)):
        raise ValueError("duplicate position symbol")
    if len(candidate_symbols) != len(set(candidate_symbols)):
        raise ValueError("duplicate candidate symbol")

    position_by_symbol = {position.symbol: position for position in positions}
    held_symbols = set(position_symbols)
    for position in positions:
        if position.price is None or position.price <= ZERO:
            raise ValueError("held position price must be positive")
        if position.market_value != Decimal(position.quantity) * position.price:
            raise ValueError("position market value must equal quantity times price")
    for candidate in candidates:
        if candidate.price <= ZERO:
            raise ValueError("candidate price must be positive")
        if candidate.symbol not in held_symbols and len(candidate.returns) < 60:
            raise ValueError("new candidate returns must contain at least 60 sessions")
        if (
            candidate.symbol in held_symbols
            and candidate.price != position_by_symbol[candidate.symbol].price
        ):
            raise ValueError("candidate price must equal held position price")


def _adjusted_scores(
    candidates: tuple[EngineCandidate, ...],
) -> dict[str, Decimal]:
    adjusted: dict[str, Decimal] = {}
    for candidate in candidates:
        volatility = Decimal(str(pstdev(candidate.returns))) if candidate.returns else ZERO
        denominator = max(volatility, MIN_VOLATILITY)
        adjusted[candidate.symbol] = max(candidate.score / denominator, ZERO)
    return adjusted


def _sum_weights(weights: dict[str, Decimal]) -> Decimal:
    return sum((weights[symbol] for symbol in sorted(weights)), ZERO)


def _allocate_capped_weights(
    profile: EngineProfile,
    candidates: tuple[EngineCandidate, ...],
    adjusted_scores: dict[str, Decimal],
) -> dict[str, Decimal]:
    weights = {candidate.symbol: ZERO for candidate in candidates}
    risky_exposure = max(ONE - profile.min_cash_ratio, ZERO)
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.symbol))
    tolerance = Decimal("1e-24")

    while risky_exposure - _sum_weights(weights) > tolerance:
        industry_weights: dict[str | None, Decimal] = {}
        for candidate in ordered:
            industry_weights[candidate.industry] = (
                industry_weights.get(candidate.industry, ZERO) + weights[candidate.symbol]
            )

        active = [
            candidate
            for candidate in ordered
            if adjusted_scores[candidate.symbol] > ZERO
            and weights[candidate.symbol] < profile.max_stock_weight
            and industry_weights[candidate.industry] < profile.max_industry_weight
        ]
        if not active:
            break

        remaining = risky_exposure - _sum_weights(weights)
        active_score = sum(
            (adjusted_scores[candidate.symbol] for candidate in active), ZERO
        )
        if active_score <= ZERO:
            break
        increments = {
            candidate.symbol: remaining * adjusted_scores[candidate.symbol] / active_score
            for candidate in active
        }

        by_industry: dict[str | None, list[EngineCandidate]] = {}
        for candidate in active:
            by_industry.setdefault(candidate.industry, []).append(candidate)
        for industry, members in by_industry.items():
            proposed = sum((increments[member.symbol] for member in members), ZERO)
            capacity = max(profile.max_industry_weight - industry_weights[industry], ZERO)
            if proposed > capacity and proposed > ZERO:
                scale = capacity / proposed
                for member in members:
                    increments[member.symbol] *= scale

        progress = ZERO
        for candidate in active:
            increment = min(
                increments[candidate.symbol],
                max(profile.max_stock_weight - weights[candidate.symbol], ZERO),
            )
            weights[candidate.symbol] += increment
            progress += increment
        if progress <= tolerance:
            break

    return weights


def _portfolio_return_series(
    candidates: tuple[EngineCandidate, ...], weights: dict[str, Decimal]
) -> tuple[float, ...]:
    active = sorted(
        (
            candidate
            for candidate in candidates
            if weights.get(candidate.symbol, ZERO) > ZERO
        ),
        key=lambda candidate: candidate.symbol,
    )
    if not active:
        return ()
    common_length = min(MAX_RETURN_SESSIONS, *(len(candidate.returns) for candidate in active))
    if common_length == 0:
        return ()
    return tuple(
        sum(
            float(weights[candidate.symbol]) * candidate.returns[-common_length + offset]
            for candidate in active
        )
        for offset in range(common_length)
    )


def _scale_for_drawdown(
    profile: EngineProfile,
    candidates: tuple[EngineCandidate, ...],
    proposed_weights: dict[str, Decimal],
) -> tuple[dict[str, Decimal], Decimal]:
    full_series = _portfolio_return_series(candidates, proposed_weights)
    full_drawdown = historical_max_drawdown(full_series)
    if full_drawdown <= profile.max_drawdown:
        return proposed_weights, full_drawdown

    low = ZERO
    high = ONE
    for _ in range(30):
        midpoint = (low + high) / Decimal("2")
        midpoint_weights = {
            symbol: weight * midpoint for symbol, weight in proposed_weights.items()
        }
        drawdown = historical_max_drawdown(
            _portfolio_return_series(candidates, midpoint_weights)
        )
        if drawdown <= profile.max_drawdown:
            low = midpoint
        else:
            high = midpoint

    scaled = {symbol: weight * low for symbol, weight in proposed_weights.items()}
    return scaled, historical_max_drawdown(_portfolio_return_series(candidates, scaled))


def _blend_for_turnover(
    profile: EngineProfile,
    current_weights: dict[str, Decimal],
    proposed_weights: dict[str, Decimal],
    symbols: tuple[str, ...],
) -> dict[str, Decimal]:
    proposed_turnover = (
        sum(
            (
                abs(
                    proposed_weights.get(symbol, ZERO)
                    - current_weights.get(symbol, ZERO)
                )
                for symbol in symbols
            ),
            ZERO,
        )
        / Decimal("2")
    )
    if proposed_turnover <= profile.max_daily_turnover or proposed_turnover == ZERO:
        return {symbol: proposed_weights.get(symbol, ZERO) for symbol in symbols}

    blend = profile.max_daily_turnover / proposed_turnover
    return {
        symbol: current_weights.get(symbol, ZERO)
        + blend * (proposed_weights.get(symbol, ZERO) - current_weights.get(symbol, ZERO))
        for symbol in symbols
    }


def _floor_lots(shares: Decimal) -> int:
    if shares <= ZERO:
        return 0
    return int((shares / LOT_SIZE).to_integral_value(rounding=ROUND_FLOOR)) * LOT_SIZE


def _target_quantities(
    total_asset: Decimal,
    target_weights: dict[str, Decimal],
    current_quantities: dict[str, int],
    prices: dict[str, Decimal],
) -> dict[str, int]:
    quantities: dict[str, int] = {}
    for symbol in sorted(target_weights):
        current = current_quantities.get(symbol, 0)
        target_weight = max(target_weights[symbol], ZERO)
        raw_target = target_weight * total_asset / prices[symbol]
        if target_weight == ZERO:
            quantities[symbol] = 0
        elif raw_target >= current:
            quantities[symbol] = current + _floor_lots(raw_target - current)
        else:
            reduction = _floor_lots(Decimal(current) - raw_target)
            quantities[symbol] = current - reduction
    return quantities


def _cash_after_trades(
    cash: Decimal,
    current_quantities: dict[str, int],
    target_quantities: dict[str, int],
    prices: dict[str, Decimal],
    estimated_cost_rate: Decimal,
) -> Decimal:
    trade_cash_flow = sum(
        (
            Decimal(current_quantities.get(symbol, 0) - target_quantity) * prices[symbol]
            for symbol, target_quantity in target_quantities.items()
        ),
        ZERO,
    )
    traded_value = sum(
        (
            Decimal(abs(target_quantity - current_quantities.get(symbol, 0)))
            * prices[symbol]
            for symbol, target_quantity in target_quantities.items()
        ),
        ZERO,
    )
    return cash + trade_cash_flow - estimated_cost_rate * traded_value


def _repair_post_rounding_caps(
    profile: EngineProfile,
    total_asset: Decimal,
    current_quantities: dict[str, int],
    target_quantities: dict[str, int],
    prices: dict[str, Decimal],
    industries: dict[str, str | None],
    candidates: dict[str, EngineCandidate],
    adjusted_scores: dict[str, Decimal],
) -> tuple[dict[str, int], set[str]]:
    quantities = dict(target_quantities)
    reduced_for_cap: set[str] = set()

    maximum_stock_value = total_asset * profile.max_stock_weight
    for symbol in sorted(quantities):
        while (
            quantities[symbol] - current_quantities.get(symbol, 0) >= LOT_SIZE
            and Decimal(quantities[symbol]) * prices[symbol] > maximum_stock_value
        ):
            quantities[symbol] -= LOT_SIZE
            reduced_for_cap.add(symbol)

    maximum_industry_value = total_asset * profile.max_industry_weight
    industry_order = sorted(
        set(industries.values()),
        key=lambda value: "unknown" if value is None else value,
    )
    for industry in industry_order:
        while (
            sum(
                (
                    Decimal(quantities[symbol]) * prices[symbol]
                    for symbol in sorted(quantities)
                    if industries[symbol] == industry
                ),
                ZERO,
            )
            > maximum_industry_value
        ):
            eligible = sorted(
                (
                    symbol
                    for symbol in quantities
                    if industries[symbol] == industry
                    and quantities[symbol] - current_quantities.get(symbol, 0) >= LOT_SIZE
                ),
                key=lambda symbol: (
                    adjusted_scores.get(symbol, ZERO),
                    -candidates[symbol].rank,
                    symbol,
                ),
            )
            if not eligible:
                break
            symbol = eligible[0]
            quantities[symbol] -= LOT_SIZE
            reduced_for_cap.add(symbol)

    return quantities, reduced_for_cap


def _reserve_costs(
    cash: Decimal,
    minimum_cash: Decimal,
    current_quantities: dict[str, int],
    target_quantities: dict[str, int],
    prices: dict[str, Decimal],
    candidates: dict[str, EngineCandidate],
    adjusted_scores: dict[str, Decimal],
    estimated_cost_rate: Decimal,
) -> tuple[dict[str, int], Decimal, set[str]]:
    quantities = dict(target_quantities)
    reduced_for_cost: set[str] = set()
    buy_order = sorted(
        (
            symbol
            for symbol, target in quantities.items()
            if target > current_quantities.get(symbol, 0)
        ),
        key=lambda symbol: (
            adjusted_scores.get(symbol, ZERO),
            -candidates[symbol].rank,
            symbol,
        ),
    )
    estimated_cash = _cash_after_trades(
        cash, current_quantities, quantities, prices, estimated_cost_rate
    )
    for symbol in buy_order:
        while (
            estimated_cash < ZERO or estimated_cash < minimum_cash
        ) and quantities[symbol] > current_quantities.get(symbol, 0):
            quantities[symbol] -= LOT_SIZE
            reduced_for_cost.add(symbol)
            estimated_cash = _cash_after_trades(
                cash, current_quantities, quantities, prices, estimated_cost_rate
            )
        if estimated_cash >= ZERO and estimated_cash >= minimum_cash:
            break
    return quantities, estimated_cash, reduced_for_cost


def _action(current_quantity: int, target_quantity: int) -> AdviceAction:
    if current_quantity > 0 and target_quantity == 0:
        return "exit"
    if target_quantity < current_quantity:
        return "reduce"
    if current_quantity == 0 and target_quantity > 0:
        return "buy"
    if target_quantity > current_quantity:
        return "increase"
    return "hold"


def _remaining_constraint_violations(
    profile: EngineProfile,
    estimated_cash: Decimal,
    total_asset: Decimal,
    target_weights: dict[str, Decimal],
    industries: dict[str, str | None],
) -> tuple[tuple[str, ...], set[str], set[str | None], bool]:
    cash_below_minimum = estimated_cash < total_asset * profile.min_cash_ratio
    stock_exceeded = {
        symbol
        for symbol, target_weight in target_weights.items()
        if target_weight > profile.max_stock_weight
    }
    industry_weights: dict[str | None, Decimal] = {}
    for symbol in sorted(target_weights):
        industry = industries[symbol]
        industry_weights[industry] = (
            industry_weights.get(industry, ZERO) + target_weights[symbol]
        )
    industry_exceeded = {
        industry
        for industry, target_weight in industry_weights.items()
        if target_weight > profile.max_industry_weight
    }

    violations: list[str] = []
    if cash_below_minimum:
        violations.append("cash_below_minimum")
    violations.extend(f"stock_cap_exceeded:{symbol}" for symbol in sorted(stock_exceeded))
    violations.extend(
        f"industry_cap_exceeded:{'unknown' if industry is None else industry}"
        for industry in sorted(
            industry_exceeded,
            key=lambda value: "unknown" if value is None else value,
        )
    )
    return tuple(violations), stock_exceeded, industry_exceeded, cash_below_minimum


def build_advice(
    profile: EngineProfile,
    cash: Decimal,
    positions: tuple[EnginePosition, ...],
    candidates: tuple[EngineCandidate, ...],
    estimated_cost_rate: Decimal,
) -> EngineResult:
    """Build constrained target quantities without external state or side effects."""
    _validate_inputs(cash, positions, candidates, estimated_cost_rate)
    position_by_symbol = {position.symbol: position for position in positions}
    candidate_by_symbol = {candidate.symbol: candidate for candidate in candidates}
    all_symbols = tuple(sorted(set(position_by_symbol) | set(candidate_by_symbol)))

    total_asset = cash + sum(
        (position_by_symbol[symbol].market_value for symbol in sorted(position_by_symbol)),
        ZERO,
    )
    current_weights = {
        position.symbol: position.market_value / total_asset for position in positions
    }
    current_quantities = {
        position.symbol: position.quantity for position in positions
    }

    adjusted_scores = _adjusted_scores(candidates)
    proposed_weights = _allocate_capped_weights(profile, candidates, adjusted_scores)
    proposed_weights, scenario_drawdown = _scale_for_drawdown(
        profile, candidates, proposed_weights
    )
    blended_weights = _blend_for_turnover(
        profile, current_weights, proposed_weights, all_symbols
    )

    prices = {
        symbol: (
            candidate_by_symbol[symbol].price
            if symbol in candidate_by_symbol
            else position_by_symbol[symbol].price
        )
        for symbol in all_symbols
    }
    # Input validation guarantees held prices are present.
    concrete_prices = {symbol: price for symbol, price in prices.items() if price is not None}
    industries = {
        symbol: (
            candidate_by_symbol[symbol].industry
            if symbol in candidate_by_symbol
            else position_by_symbol[symbol].industry
        )
        for symbol in all_symbols
    }
    targets = _target_quantities(
        total_asset, blended_weights, current_quantities, concrete_prices
    )
    targets, reduced_for_cap = _repair_post_rounding_caps(
        profile,
        total_asset,
        current_quantities,
        targets,
        concrete_prices,
        industries,
        candidate_by_symbol,
        adjusted_scores,
    )
    targets, estimated_cash, reduced_for_cost = _reserve_costs(
        cash,
        total_asset * profile.min_cash_ratio,
        current_quantities,
        targets,
        concrete_prices,
        candidate_by_symbol,
        adjusted_scores,
        estimated_cost_rate,
    )

    target_weights = {
        symbol: Decimal(targets[symbol]) * concrete_prices[symbol] / total_asset
        for symbol in all_symbols
    }
    (
        constraint_violations,
        stock_exceeded,
        industry_exceeded,
        cash_below_minimum,
    ) = _remaining_constraint_violations(
        profile, estimated_cash, total_asset, target_weights, industries
    )

    lines: list[EngineLine] = []
    for symbol in all_symbols:
        position = position_by_symbol.get(symbol)
        candidate = candidate_by_symbol.get(symbol)
        current_quantity = current_quantities.get(symbol, 0)
        target_quantity = targets[symbol]
        reference_price = concrete_prices[symbol]
        notes = [
            "已按约束优先级生成当前可执行目标"
            if constraint_violations
            else "已应用个股、行业、回撤、换手与整手约束"
        ]
        if candidate is None:
            notes.append("不在当日候选范围")
        if symbol in reduced_for_cost:
            notes.append("为预留交易成本下调买入数量")
        if symbol in reduced_for_cap:
            notes.append("为修复整手取整后的集中度下调买入数量")
        if cash_below_minimum and (current_quantity > 0 or target_quantity > 0):
            notes.append("受单日换手率或A股整手交易限制，预计现金仍低于最低现金要求")
        if symbol in stock_exceeded:
            notes.append("受单日换手率或A股整手交易限制，个股权重仍高于上限")
        if industries[symbol] in industry_exceeded and target_quantity > 0:
            if industries[symbol] is None:
                notes.append("受单日换手率或A股整手交易限制，未分类行业权重仍高于上限")
            else:
                notes.append(
                    f"受单日换手率或A股整手交易限制，{industries[symbol]}行业权重仍高于上限"
                )
        lines.append(
            EngineLine(
                symbol=symbol,
                name=candidate.name if candidate else position.name,
                industry=candidate.industry if candidate else position.industry,
                action=_action(current_quantity, target_quantity),
                current_quantity=current_quantity,
                target_quantity=target_quantity,
                delta_quantity=target_quantity - current_quantity,
                current_weight=current_weights.get(symbol, ZERO),
                target_weight=target_weights[symbol],
                reference_price=reference_price,
                price_tolerance=profile.price_tolerance,
                score=candidate.score if candidate else ZERO,
                rank=candidate.rank if candidate else None,
                confidence=candidate.confidence if candidate else "normal",
                positive_factors=candidate.positive_factors if candidate else (),
                risks=candidate.risks if candidate else ("不在当日候选范围",),
                constraint_notes=tuple(notes),
            )
        )

    lines.sort(key=lambda line: (ACTION_PRIORITY[line.action], line.symbol))
    turnover = (
        sum((abs(line.target_weight - line.current_weight) for line in lines), ZERO)
        / Decimal("2")
    )
    return EngineResult(
        current_exposure=sum(
            (current_weights[symbol] for symbol in sorted(current_weights)), ZERO
        ),
        target_exposure=sum((line.target_weight for line in lines), ZERO),
        estimated_cash=estimated_cash,
        total_asset=total_asset,
        historical_max_drawdown=scenario_drawdown,
        turnover=turnover,
        constraint_violations=constraint_violations,
        lines=tuple(lines),
    )
