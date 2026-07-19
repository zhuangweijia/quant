from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.config import Settings
from app.services.advice_engine import (
    EngineCandidate,
    EnginePosition,
    EngineProfile,
    build_advice,
    historical_max_drawdown,
)


def candidate(
    symbol: str,
    industry: str,
    score: str,
    price: str = "10",
    returns: list[float] | None = None,
    rank: int = 1,
) -> EngineCandidate:
    return EngineCandidate(
        symbol=symbol,
        name=symbol,
        industry=industry,
        score=Decimal(score),
        rank=rank,
        confidence="normal",
        price=Decimal(price),
        returns=tuple(returns if returns is not None else [0.001, -0.001] * 60),
        positive_factors=("评分靠前",),
        risks=("历史波动",),
    )


PROFILE = EngineProfile(
    max_drawdown=Decimal("0.15"),
    max_stock_weight=Decimal("0.10"),
    max_industry_weight=Decimal("0.20"),
    min_cash_ratio=Decimal("0.10"),
    max_daily_turnover=Decimal("0.30"),
    price_tolerance=Decimal("0.03"),
)

UNCONSTRAINED = EngineProfile(
    max_drawdown=Decimal("1"),
    max_stock_weight=Decimal("1"),
    max_industry_weight=Decimal("1"),
    min_cash_ratio=Decimal("0"),
    max_daily_turnover=Decimal("1"),
    price_tolerance=Decimal("0.03"),
)


def test_engine_respects_stock_industry_cash_turnover_and_lots():
    result = build_advice(
        PROFILE,
        Decimal("100000"),
        (),
        (
            candidate("000001", "银行", "0.9"),
            candidate("000002", "银行", "0.8"),
            candidate("000003", "医药", "0.7"),
            candidate("000004", "消费", "0.6"),
        ),
        Decimal("0.001"),
    )

    assert all(line.target_weight <= PROFILE.max_stock_weight for line in result.lines)
    assert (
        sum(line.target_weight for line in result.lines if line.industry == "银行")
        <= PROFILE.max_industry_weight
    )
    assert result.estimated_cash >= result.total_asset * PROFILE.min_cash_ratio
    assert result.turnover <= PROFILE.max_daily_turnover
    assert all(line.target_quantity % 100 == 0 for line in result.lines if line.delta_quantity > 0)


def test_engine_redistributes_weight_after_stock_and_industry_caps():
    profile = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=Decimal("0.20"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )
    result = build_advice(
        profile,
        Decimal("100000"),
        (),
        (
            candidate("000001", "银行", "100"),
            candidate("000002", "银行", "90"),
            candidate("000003", "医药", "2"),
            candidate("000004", "消费", "1"),
        ),
        Decimal("0"),
    )

    by_symbol = {line.symbol: line for line in result.lines}
    bank_weight = by_symbol["000001"].target_weight + by_symbol["000002"].target_weight
    assert bank_weight <= profile.max_industry_weight
    assert by_symbol["000003"].target_weight == Decimal("0.2")
    assert by_symbol["000004"].target_weight == Decimal("0.2")


def test_engine_scales_exposure_to_historical_drawdown_limit():
    stressed_profile = EngineProfile(
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("1"),
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )
    stressed = candidate(
        "000001", "银行", "0.9", returns=[-0.05] * 10 + [0.01] * 110
    )

    result = build_advice(
        stressed_profile, Decimal("100000"), (), (stressed,), Decimal("0")
    )

    assert result.historical_max_drawdown <= stressed_profile.max_drawdown
    assert Decimal("0") < result.target_exposure < Decimal("1")


def test_engine_aligns_mismatched_return_series_by_their_common_tail():
    old_losses = candidate(
        "000001", "银行", "1", returns=[-0.50] * 60 + [0.0] * 60
    )
    short_flat = candidate("000002", "医药", "1", returns=[0.0] * 60)

    result = build_advice(
        UNCONSTRAINED,
        Decimal("100000"),
        (),
        (old_losses, short_flat),
        Decimal("0"),
    )

    assert result.historical_max_drawdown == Decimal("0.0")


def test_historical_max_drawdown_is_a_decimal_peak_to_trough_result():
    result = historical_max_drawdown((0.10, -0.20, 0.10))

    assert result == Decimal("0.19999999999999996")
    assert isinstance(result, Decimal)


def test_engine_blends_proposal_to_daily_turnover_limit():
    profile = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=Decimal("1"),
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0"),
        max_daily_turnover=Decimal("0.05"),
        price_tolerance=Decimal("0.03"),
    )
    held = EnginePosition(
        "600000", "浦发银行", "银行", 5000, Decimal("10"), Decimal("50000")
    )

    result = build_advice(
        profile,
        Decimal("50000"),
        (held,),
        (candidate("600000", "银行", "-1"),),
        Decimal("0"),
    )

    line = result.lines[0]
    assert line.target_quantity == 4000
    assert result.turnover == Decimal("0.05")


def test_engine_emits_exit_for_held_stock_outside_candidates():
    held = EnginePosition(
        "600000", "浦发银行", "银行", 1055, Decimal("10"), Decimal("10550")
    )

    result = build_advice(
        PROFILE, Decimal("90000"), (held,), (), Decimal("0.001")
    )

    line = next(item for item in result.lines if item.symbol == "600000")
    assert line.action == "exit"
    assert line.target_quantity == 0
    assert line.delta_quantity == -1055


def test_engine_rounds_increases_and_reductions_by_trade_lot():
    profile = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=Decimal("0.50"),
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0.50"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )
    odd_lot = EnginePosition(
        "000001", "平安银行", "银行", 155, Decimal("10"), Decimal("1550")
    )
    result = build_advice(
        profile,
        Decimal("98450"),
        (odd_lot,),
        (
            candidate("000001", "银行", "100"),
            candidate("000002", "医药", "1"),
        ),
        Decimal("0"),
    )
    by_symbol = {line.symbol: line for line in result.lines}

    assert by_symbol["000001"].delta_quantity % 100 == 0
    assert by_symbol["000001"].target_quantity % 100 == 55
    assert by_symbol["000002"].target_quantity % 100 == 0


def test_engine_holds_when_a_non_exit_reduction_is_smaller_than_one_lot():
    held = EnginePosition("000001", "平安银行", "银行", 155, Decimal("10"), Decimal("1550"))
    total_asset = Decimal("100000")
    desired_weight = Decimal("0.015")
    profile = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=desired_weight,
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )

    result = build_advice(
        profile,
        total_asset - held.market_value,
        (held,),
        (candidate("000001", "银行", "1"),),
        Decimal("0"),
    )

    assert result.lines[0].action == "hold"
    assert result.lines[0].target_quantity == 155


def test_engine_reduces_buys_to_reserve_transaction_cost_and_minimum_cash():
    # With a 10% cash floor, 900 shares would leave 9,910 after costs.
    profile_with_cash_floor = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=Decimal("1"),
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )
    result = build_advice(
        profile_with_cash_floor,
        Decimal("100000"),
        (),
        (candidate("000001", "银行", "1", price="100"),),
        Decimal("0.001"),
    )

    assert result.lines[0].target_quantity == 800
    assert result.estimated_cash == Decimal("19920.000")


def test_cost_reserve_loop_terminates_when_all_buys_must_be_removed():
    result = build_advice(
        PROFILE,
        Decimal("100000"),
        (),
        (candidate("000001", "银行", "1", price="100"),),
        Decimal("100"),
    )

    assert result.lines[0].target_quantity == 0
    assert result.estimated_cash == Decimal("100000")


@pytest.mark.parametrize(
    ("cash", "positions", "candidates", "message"),
    [
        (Decimal("0"), (), (), "cash"),
        (
            Decimal("1"),
            (),
            (candidate("000001", "银行", "1", price="0"),),
            "price",
        ),
        (
            Decimal("1"),
            (EnginePosition("000001", "平安银行", "银行", 100, None, Decimal("1000")),),
            (),
            "price",
        ),
        (
            Decimal("1"),
            (),
            (candidate("000001", "银行", "1", returns=[0.0] * 59),),
            "returns",
        ),
        (
            Decimal("1"),
            (),
            (candidate("000001", "银行", "1"), candidate("000001", "医药", "2")),
            "duplicate",
        ),
        (
            Decimal("1"),
            (
                EnginePosition("000001", "平安银行", "银行", 100, Decimal("10"), Decimal("1000")),
                EnginePosition("000001", "平安银行", "银行", 100, Decimal("10"), Decimal("1000")),
            ),
            (),
            "duplicate",
        ),
    ],
)
def test_engine_rejects_invalid_inputs(cash, positions, candidates, message):
    with pytest.raises(ValueError, match=message):
        build_advice(PROFILE, cash, positions, candidates, Decimal("0.001"))


def test_short_return_history_is_allowed_for_an_already_held_candidate():
    held = EnginePosition("000001", "平安银行", "银行", 100, Decimal("10"), Decimal("1000"))
    short_history = candidate("000001", "银行", "1", returns=[0.0] * 10)

    result = build_advice(
        PROFILE, Decimal("99000"), (held,), (short_history,), Decimal("0")
    )

    assert result.lines[0].symbol == "000001"


def test_non_positive_scores_produce_no_risky_allocation():
    held = EnginePosition("600000", "浦发银行", "银行", 100, Decimal("10"), Decimal("1000"))

    result = build_advice(
        PROFILE,
        Decimal("99000"),
        (held,),
        (candidate("000001", "银行", "0"), candidate("000002", "医药", "-1")),
        Decimal("0"),
    )

    assert result.target_exposure == Decimal("0")
    assert all(line.target_quantity == 0 for line in result.lines)


def test_cash_only_and_held_only_portfolios_are_deterministic():
    cash_only = build_advice(PROFILE, Decimal("100000"), (), (), Decimal("0.001"))
    held = EnginePosition("600000", "浦发银行", "银行", 100, Decimal("10"), Decimal("1000"))
    held_only = build_advice(PROFILE, Decimal("1"), (held,), (), Decimal("0.001"))

    assert cash_only.lines == ()
    assert cash_only.estimated_cash == Decimal("100000")
    assert held_only.lines[0].action == "hold"
    assert held_only.lines[0].target_quantity == 100


def test_infeasible_held_portfolio_surfaces_progressive_constraint_violations():
    held = EnginePosition("600000", "浦发银行", "银行", 100, Decimal("10"), Decimal("1000"))

    result = build_advice(PROFILE, Decimal("1"), (held,), (), Decimal("0.001"))

    assert result.turnover <= PROFILE.max_daily_turnover
    assert result.lines[0].delta_quantity % 100 == 0
    assert result.constraint_violations == (
        "cash_below_minimum",
        "stock_cap_exceeded:600000",
        "industry_cap_exceeded:银行",
    )
    notes = " ".join(result.lines[0].constraint_notes)
    assert "最低现金" in notes
    assert "个股权重" in notes
    assert "行业权重" in notes
    assert "单日换手率" in notes
    assert "整手" in notes
    assert "已应用个股、行业、回撤、换手与整手约束" not in notes


def test_feasible_result_has_no_constraint_violations():
    result = build_advice(
        PROFILE,
        Decimal("100000"),
        (),
        (candidate("000001", "银行", "1"),),
        Decimal("0.001"),
    )

    assert result.constraint_violations == ()


def test_constraint_violation_order_is_category_then_lexical_suffix():
    positions = (
        EnginePosition("000003", "科技三", "科技", 100, Decimal("10"), Decimal("1000")),
        EnginePosition("000002", "银行二", "银行", 100, Decimal("10"), Decimal("1000")),
        EnginePosition("000001", "银行一", "银行", 100, Decimal("10"), Decimal("1000")),
    )

    result = build_advice(PROFILE, Decimal("1"), positions, (), Decimal("0"))

    assert result.constraint_violations == (
        "cash_below_minimum",
        "stock_cap_exceeded:000001",
        "stock_cap_exceeded:000002",
        "stock_cap_exceeded:000003",
        "industry_cap_exceeded:科技",
        "industry_cap_exceeded:银行",
    )


def test_none_industries_share_the_unknown_violation_bucket():
    positions = (
        EnginePosition("000001", "未分类一", None, 100, Decimal("10"), Decimal("1000")),
        EnginePosition("000002", "未分类二", None, 100, Decimal("10"), Decimal("1000")),
    )

    result = build_advice(PROFILE, Decimal("1"), positions, (), Decimal("0"))

    assert "industry_cap_exceeded:unknown" in result.constraint_violations
    assert all(
        "未分类行业权重仍高于上限" in " ".join(line.constraint_notes)
        for line in result.lines
    )


def test_engine_rejects_position_market_value_mismatch():
    inconsistent = EnginePosition(
        "000001", "平安银行", "银行", 100, Decimal("10"), Decimal("999")
    )

    with pytest.raises(ValueError, match="market value"):
        build_advice(PROFILE, Decimal("1000"), (inconsistent,), (), Decimal("0"))


def test_engine_rejects_candidate_price_mismatch_for_held_symbol():
    held = EnginePosition("000001", "平安银行", "银行", 100, Decimal("10"), Decimal("1000"))
    repriced = candidate("000001", "银行", "1", price="10.01")

    with pytest.raises(ValueError, match="candidate price"):
        build_advice(PROFILE, Decimal("1000"), (held,), (repriced,), Decimal("0"))


def test_actions_have_stable_priority_then_symbol_order():
    positions = (
        EnginePosition("600004", "退出", "银行", 100, Decimal("10"), Decimal("1000")),
        EnginePosition("600002", "减持", "医药", 1000, Decimal("10"), Decimal("10000")),
        EnginePosition("600005", "持有", "消费", 100, Decimal("10"), Decimal("1000")),
    )
    profile = EngineProfile(
        max_drawdown=Decimal("1"),
        max_stock_weight=Decimal("0.10"),
        max_industry_weight=Decimal("1"),
        min_cash_ratio=Decimal("0.70"),
        max_daily_turnover=Decimal("1"),
        price_tolerance=Decimal("0.03"),
    )
    result = build_advice(
        profile,
        Decimal("88000"),
        positions,
        (
            candidate("600002", "医药", "1"),
            candidate("600003", "科技", "1"),
            candidate("600005", "消费", "0.1"),
        ),
        Decimal("0"),
    )

    priorities = {"exit": 0, "reduce": 1, "buy": 2, "increase": 3, "hold": 4}
    sort_keys = [(priorities[line.action], line.symbol) for line in result.lines]
    assert sort_keys == sorted(sort_keys)


def test_candidate_input_order_does_not_change_the_result():
    candidates = (
        candidate("000003", "消费", "0.7", returns=[0.01, -0.02] * 60),
        candidate("000001", "银行", "0.9", returns=[-0.01, 0.02] * 60),
        candidate("000002", "医药", "0.8", returns=[0.005, -0.01] * 60),
    )

    forward = build_advice(PROFILE, Decimal("100000"), (), candidates, Decimal("0.001"))
    reverse = build_advice(
        PROFILE, Decimal("100000"), (), tuple(reversed(candidates)), Decimal("0.001")
    )

    assert forward == reverse


def test_dataclasses_are_frozen_inputs_are_not_mutated_and_outputs_use_decimal():
    candidates = (candidate("000001", "银行", "1"),)
    original = candidates

    result = build_advice(PROFILE, Decimal("100000"), (), candidates, Decimal("0"))

    assert candidates == original
    with pytest.raises(FrozenInstanceError):
        candidates[0].score = Decimal("2")
    assert isinstance(result.total_asset, Decimal)
    assert isinstance(result.estimated_cash, Decimal)
    assert isinstance(result.turnover, Decimal)
    assert isinstance(result.historical_max_drawdown, Decimal)
    assert all(isinstance(line.target_weight, Decimal) for line in result.lines)


def test_settings_expose_advice_engine_defaults():
    settings = Settings()

    assert settings.TRANSACTION_COST_BUFFER_RATE == 0.001
    assert settings.ADVICE_PRICE_TOLERANCE == 0.03
