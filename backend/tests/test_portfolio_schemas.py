import json
from datetime import datetime, tzinfo
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.advice import AdviceTodayResponse, DailyAdviceResponse, ExecutionUpdateRequest
from app.schemas.portfolio import (
    CashMovementRequest,
    HoldingsReconcileRequest,
    InvestmentProfileInput,
    MonetaryDecimal,
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
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(disposition="skipped", fee=Decimal("0.01"), expected_revision=0)


def test_skipped_execution_requires_a_nonblank_reason():
    with pytest.raises(ValidationError, match="原因"):
        ExecutionUpdateRequest(disposition="skipped", expected_revision=0)
    with pytest.raises(ValidationError, match="原因"):
        ExecutionUpdateRequest(
            disposition="skipped", reason=" \t\r\n", expected_revision=0
        )

    request = ExecutionUpdateRequest(
        disposition="skipped", reason="临时资金安排", expected_revision=0
    )
    assert request.reason == "临时资金安排"


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


def test_reconcile_accepts_current_cash():
    reconcile = HoldingsReconcileRequest(
        expected_updated_at="2026-07-19T09:00:00+08:00",
        cash=Decimal("100.0001"),
        positions=[],
    )

    assert reconcile.cash == Decimal("100.0001")


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
    complete = PortfolioSetupStatus(has_profile=True, has_portfolio=True)
    partial = PortfolioSetupStatus(has_profile=True, has_portfolio=False)
    assert complete.complete is True
    assert complete.missing == []
    assert partial.complete is False
    assert partial.missing == ["portfolio"]
    with pytest.raises(ValidationError):
        PortfolioSetupStatus(has_profile=True, has_portfolio=False, complete=True)
    with pytest.raises(ValidationError):
        PortfolioSetupStatus(has_profile=False, has_portfolio=True, missing=[])
    with pytest.raises(ValidationError):
        AdviceTodayResponse(state="ready")


def test_ratio_decimal_serializes_as_a_json_number():
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


def test_money_decimal_serializes_as_an_exact_json_string():
    setup = PortfolioSetupRequest(
        profile=balanced_profile(),
        total_capital=Decimal("10000000000000.0001"),
        cash=Decimal("10000000000000.0001"),
    )
    assert setup.total_capital == Decimal("10000000000000.0001")
    assert '"total_capital":"10000000000000.0001"' in setup.model_dump_json()


def test_derived_money_response_values_may_keep_more_than_four_decimal_places():
    derived = TypeAdapter(MonetaryDecimal).validate_python(Decimal("3.33333333"))

    assert derived == Decimal("3.33333333")


def test_money_fields_reject_values_outside_numeric_20_4():
    occurred_at = "2026-07-19T09:00:00+08:00"

    with pytest.raises(ValidationError):
        CashMovementRequest(
            kind="deposit", amount=Decimal("0.00001"), occurred_at=occurred_at
        )
    with pytest.raises(ValidationError):
        PortfolioSetupRequest(
            profile=balanced_profile(),
            total_capital=Decimal("10000000000000000.0000"),
            cash=Decimal("0"),
        )
    with pytest.raises(ValidationError):
        HoldingsReconcileRequest(
            expected_updated_at=occurred_at,
            cash=Decimal("1.00001"),
            positions=[],
        )
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(
            disposition="executed",
            quantity=1,
            price=Decimal("10.00001"),
            executed_at=occurred_at,
            expected_revision=0,
        )


def test_money_fields_require_quoted_decimal_json_tokens():
    quoted_reconcile = {
        "expected_updated_at": "2026-07-19T09:00:00+08:00",
        "cash": "100.0001",
        "positions": [],
    }
    reconcile = HoldingsReconcileRequest.model_validate_json(json.dumps(quoted_reconcile))
    assert reconcile.cash == Decimal("100.0001")
    with pytest.raises(ValidationError):
        HoldingsReconcileRequest.model_validate_json(
            json.dumps({**quoted_reconcile, "cash": 100.0001})
        )

    quoted_cash_movement = {
        "kind": "deposit",
        "amount": "25.0001",
        "occurred_at": "2026-07-19T09:00:00+08:00",
    }
    assert CashMovementRequest.model_validate_json(
        json.dumps(quoted_cash_movement)
    ).amount == Decimal("25.0001")
    with pytest.raises(ValidationError):
        CashMovementRequest.model_validate_json(
            json.dumps({**quoted_cash_movement, "amount": 25.0001})
        )

    quoted_setup = {
        "profile": {
            "investment_horizon_days": 120,
            "risk_level": "balanced",
            "max_drawdown": 0.15,
            "max_stock_weight": 0.08,
            "max_industry_weight": 0.25,
            "min_cash_ratio": 0.1,
            "max_daily_turnover": 0.3,
        },
        "total_capital": "1000.0001",
        "cash": "900.0001",
        "positions": [{"symbol": "000001", "quantity": 10, "average_cost": "10"}],
    }
    setup = PortfolioSetupRequest.model_validate_json(json.dumps(quoted_setup))
    assert setup.cash == Decimal("900.0001")
    for field in ("total_capital", "cash"):
        with pytest.raises(ValidationError):
            PortfolioSetupRequest.model_validate_json(
                json.dumps({**quoted_setup, field: 1000.0001})
            )
    with pytest.raises(ValidationError):
        PortfolioSetupRequest.model_validate_json(
            json.dumps(
                {
                    **quoted_setup,
                    "positions": [
                        {"symbol": "000001", "quantity": 10, "average_cost": 10}
                    ],
                }
            )
        )

    quoted_execution = {
        "disposition": "executed",
        "quantity": 1,
        "price": "10.0001",
        "fee": "0.0001",
        "executed_at": "2026-07-19T09:00:00+08:00",
        "expected_revision": 0,
    }
    assert ExecutionUpdateRequest.model_validate_json(
        json.dumps(quoted_execution)
    ).price == Decimal("10.0001")
    for field in ("price", "fee"):
        with pytest.raises(ValidationError):
            ExecutionUpdateRequest.model_validate_json(
                json.dumps({**quoted_execution, field: 10.0001})
            )

    profile = InvestmentProfileInput.model_validate_json(json.dumps(quoted_setup["profile"]))
    assert profile.max_drawdown == Decimal("0.15")


class NoneOffsetTimezone(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None

    def tzname(self, dt):
        return "none-offset"


def test_none_offset_timezones_are_rejected():
    none_offset = datetime(2026, 7, 19, 9, 0, tzinfo=NoneOffsetTimezone())
    with pytest.raises(ValidationError):
        HoldingsReconcileRequest(expected_updated_at=none_offset, positions=[])
    with pytest.raises(ValidationError):
        CashMovementRequest(kind="deposit", amount=Decimal("1"), occurred_at=none_offset)
    with pytest.raises(ValidationError):
        ExecutionUpdateRequest(
            disposition="executed",
            quantity=1,
            price=Decimal("1"),
            executed_at=none_offset,
            expected_revision=0,
        )


def test_daily_advice_serializes_money_exactly_and_exposes_constraint_codes():
    advice = DailyAdviceResponse(
        id="00000000-0000-0000-0000-000000000001",
        signal_date="2026-07-17",
        version=1,
        status="ready",
        model_version="model-v1",
        data_date="2026-07-17",
        current_exposure=Decimal("0.2"),
        target_exposure=Decimal("0.3"),
        current_cash=Decimal("8000.0001"),
        estimated_cash=Decimal("7000.0001"),
        total_asset=Decimal("10000.0001"),
        generated_at="2026-07-17T09:00:00+00:00",
        portfolio_updated_at="2026-07-17T08:00:00+00:00",
        stale_warnings=[],
        constraint_violations=["cash_below_minimum", "stock_cap_exceeded:000001"],
    )

    encoded = advice.model_dump_json()
    assert advice.constraint_violations == [
        "cash_below_minimum",
        "stock_cap_exceeded:000001",
    ]
    assert '"estimated_cash":"7000.0001"' in encoded
    assert '"target_exposure":0.3' in encoded
