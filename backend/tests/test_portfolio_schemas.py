from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.advice import AdviceTodayResponse, ExecutionUpdateRequest
from app.schemas.portfolio import (
    CashMovementRequest,
    HoldingsReconcileRequest,
    InvestmentProfileInput,
    PortfolioSetupRequest,
    PortfolioSetupStatus,
    PositionInput,
)


def balanced_profile(**changes):
    values = dict(
        investment_horizon_days=120,
        risk_level="balanced",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.08"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )
    values.update(changes)
    return InvestmentProfileInput(**values)


def test_profile_rejects_incoherent_constraints():
    with pytest.raises(ValidationError):
        balanced_profile(max_stock_weight=Decimal("0.30"), max_industry_weight=Decimal("0.20"))
    with pytest.raises(ValidationError):
        balanced_profile(min_cash_ratio=Decimal("0.80"))


def test_setup_rejects_duplicate_symbols():
    position = PositionInput(symbol="000001", quantity=100, average_cost=Decimal("10"))
    with pytest.raises(ValidationError):
        PortfolioSetupRequest(
            profile=balanced_profile(), total_capital=Decimal("10000"), cash=Decimal("9000"),
            positions=[position, position],
        )


def test_skipped_execution_rejects_trade_fields():
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(
            disposition="skipped", quantity=100, price=Decimal("10"), expected_revision=0,
        )


def test_profile_accepts_boundaries_and_rejects_extra_fields():
    profile = InvestmentProfileInput(
        investment_horizon_days=20,
        risk_level="conservative",
        max_drawdown=Decimal("0.03"),
        max_stock_weight=Decimal("0.01"),
        max_industry_weight=Decimal("0.05"),
        min_cash_ratio=Decimal("0"),
        max_daily_turnover=Decimal("0.05"),
    )
    assert profile.max_drawdown == Decimal("0.03")
    with pytest.raises(ValidationError):
        InvestmentProfileInput(**profile.model_dump(), unexpected=True)


def test_reconcile_and_cash_movement_require_aware_datetimes():
    with pytest.raises(ValidationError):
        HoldingsReconcileRequest(expected_updated_at="2026-07-19T09:00:00", positions=[])
    with pytest.raises(ValidationError):
        CashMovementRequest(
            kind="deposit", amount=Decimal("1"), occurred_at="2026-07-19T09:00:00"
        )


def test_executed_execution_requires_aware_trade_details():
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(disposition="executed", expected_revision=0)
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(
            disposition="partial",
            quantity=1,
            price=Decimal("1"),
            executed_at="2026-07-19T09:00:00",
            expected_revision=0,
        )


def test_setup_status_and_today_advice_enforce_contract_state():
    status = PortfolioSetupStatus(complete=False, has_profile=False, has_portfolio=False)
    assert status.missing == []
    with pytest.raises(ValidationError):
        AdviceTodayResponse(state="ready")


def test_profile_serializes_decimal_as_a_json_number():
    profile = InvestmentProfileInput(
        investment_horizon_days=120,
        risk_level="balanced",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.08"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )
    assert '"max_drawdown":0.15' in profile.model_dump_json()
