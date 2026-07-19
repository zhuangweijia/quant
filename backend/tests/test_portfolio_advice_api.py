from datetime import UTC, date, datetime
from decimal import Decimal
from inspect import signature
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import advice as advice_api
from app.api.v1 import portfolio as portfolio_api
from app.main import app
from app.schemas.advice import ExecutionUpdateRequest
from app.schemas.portfolio import (
    CashMovementRequest,
    HoldingsReconcileRequest,
    InvestmentProfileInput,
    PortfolioSetupRequest,
)


def profile_payload():
    return InvestmentProfileInput(
        investment_horizon_days=120,
        risk_level="balanced",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.08"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )


@pytest.mark.asyncio
async def test_setup_status_passes_current_user_id(monkeypatch):
    get_status = AsyncMock(return_value=SimpleNamespace())
    monkeypatch.setattr(portfolio_api.portfolio_service, "get_setup_status", get_status)
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    response = await portfolio_api.setup_status(user=user, db=db)

    get_status.assert_awaited_once_with(db, user.id)
    assert response.data is not None


@pytest.mark.asyncio
async def test_setup_uses_current_user_id_and_payload_has_no_user_id(monkeypatch):
    complete_setup = AsyncMock(return_value=SimpleNamespace())
    monkeypatch.setattr(portfolio_api.portfolio_service, "complete_setup", complete_setup)
    monkeypatch.setattr(
        portfolio_api, "extract_request_info", lambda request: ("127.0.0.1", "test")
    )
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")
    payload = PortfolioSetupRequest(
        profile=profile_payload(), total_capital=Decimal("10000"), cash=Decimal("10000")
    )

    await portfolio_api.setup_portfolio(
        user=user,
        db=db,
        payload=payload,
        request=SimpleNamespace(client=None, headers={}),
    )

    assert "user_id" not in type(payload).model_fields
    complete_setup.assert_awaited_once_with(db, user.id, payload, ("127.0.0.1", "test"))


@pytest.mark.asyncio
async def test_get_portfolio_passes_current_user_id(monkeypatch):
    get_response = AsyncMock(return_value=SimpleNamespace())
    monkeypatch.setattr(portfolio_api.portfolio_service, "get_portfolio_response", get_response)
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    await portfolio_api.get_portfolio(user=user, db=db)

    get_response.assert_awaited_once_with(db, user.id)


@pytest.mark.asyncio
async def test_profile_update_passes_current_user_id(monkeypatch):
    create_version = AsyncMock(return_value=SimpleNamespace())
    monkeypatch.setattr(portfolio_api.portfolio_service, "create_profile_version", create_version)
    monkeypatch.setattr(
        portfolio_api, "extract_request_info", lambda request: ("127.0.0.1", "test")
    )
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")
    payload = profile_payload()

    await portfolio_api.update_profile(
        user=user,
        db=db,
        payload=payload,
        request=SimpleNamespace(client=None, headers={}),
    )

    create_version.assert_awaited_once_with(db, user.id, payload, ("127.0.0.1", "test"))


@pytest.mark.asyncio
async def test_reconcile_and_cash_routes_use_current_user_id(monkeypatch):
    reconcile = AsyncMock(return_value=SimpleNamespace())
    cash_movement = AsyncMock(return_value=SimpleNamespace())
    monkeypatch.setattr(portfolio_api.portfolio_service, "reconcile_holdings", reconcile)
    monkeypatch.setattr(portfolio_api.portfolio_service, "record_cash_movement", cash_movement)
    monkeypatch.setattr(
        portfolio_api, "extract_request_info", lambda request: ("127.0.0.1", "test")
    )
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")
    holdings = HoldingsReconcileRequest(
        expected_updated_at=datetime(2026, 7, 19, 9, tzinfo=UTC), cash=Decimal("100")
    )
    movement = CashMovementRequest(
        kind="deposit",
        amount=Decimal("25"),
        occurred_at=datetime(2026, 7, 19, 9, tzinfo=UTC),
    )
    request = SimpleNamespace(client=None, headers={})

    await portfolio_api.reconcile_holdings(user=user, db=db, payload=holdings, request=request)
    await portfolio_api.record_cash_movement(user=user, db=db, payload=movement, request=request)

    reconcile.assert_awaited_once_with(db, user.id, holdings, ("127.0.0.1", "test"))
    cash_movement.assert_awaited_once_with(db, user.id, movement, ("127.0.0.1", "test"))


@pytest.mark.asyncio
async def test_advice_today_uses_authenticated_user_and_returns_business_state(monkeypatch):
    state = SimpleNamespace(state="not_generated")
    get_today = AsyncMock(return_value=state)
    monkeypatch.setattr(advice_api.advice_service, "get_today_state", get_today)
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    response = await advice_api.get_today_advice(user=user, db=db)

    get_today.assert_awaited_once_with(db, user.id)
    assert response.data is state


@pytest.mark.asyncio
async def test_generate_uses_latest_ranked_date_and_authenticated_user(monkeypatch):
    generated = SimpleNamespace(id="advice-1")
    response = SimpleNamespace(id="advice-1")
    monkeypatch.setattr(
        advice_api.advice_service,
        "latest_ranked_signal_date",
        AsyncMock(return_value=date(2026, 7, 17)),
    )
    generate = AsyncMock(return_value=generated)
    monkeypatch.setattr(advice_api.advice_service, "generate_for_user", generate)
    monkeypatch.setattr(
        advice_api.advice_service, "get_advice_response", AsyncMock(return_value=response)
    )
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")

    result = await advice_api.generate_advice(user=user, db=db, force=True)

    generate.assert_awaited_once_with(db, user.id, date(2026, 7, 17), force=True)
    assert result.data is response


@pytest.mark.asyncio
async def test_generate_returns_409_when_ranked_predictions_are_missing(monkeypatch):
    monkeypatch.setattr(
        advice_api.advice_service,
        "latest_ranked_signal_date",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as exc:
        await advice_api.generate_advice(
            user=SimpleNamespace(id="user-1"), db=SimpleNamespace(), force=False
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "ranked_predictions_missing"
    assert (
        exc.value.detail["message"]
        == "暂无可用的当日排名，请等待分析完成后再生成建议"
    )


@pytest.mark.asyncio
async def test_execution_route_uses_authenticated_user_and_request_metadata(monkeypatch):
    expected = SimpleNamespace(item=SimpleNamespace())
    update_execution = AsyncMock(return_value=expected)
    monkeypatch.setattr(advice_api.execution_service, "update_execution", update_execution)
    monkeypatch.setattr(
        advice_api, "extract_request_info", lambda request: ("127.0.0.1", "pytest")
    )
    db = SimpleNamespace()
    user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001")
    payload = ExecutionUpdateRequest(
        disposition="skipped", reason="本次不执行", expected_revision=0
    )

    response = await advice_api.record_execution(
        user=user,
        db=db,
        item_id="00000000-0000-0000-0000-000000000010",
        payload=payload,
        idempotency_key="key-12345678",
        request=SimpleNamespace(client=None, headers={}),
    )

    update_execution.assert_awaited_once_with(
        db,
        user.id,
        "00000000-0000-0000-0000-000000000010",
        payload,
        "key-12345678",
        ("127.0.0.1", "pytest"),
    )
    assert response.data is expected


def test_execution_api_requires_bounded_idempotency_header_and_forbids_owner_ids():
    operation = app.openapi()["paths"]["/api/v1/advice/items/{item_id}/execution"]["put"]
    header = next(parameter for parameter in operation["parameters"] if parameter["in"] == "header")
    fields = signature(ExecutionUpdateRequest).parameters

    assert header["name"] == "Idempotency-Key"
    assert header["required"] is True
    assert header["schema"]["minLength"] == 8
    assert header["schema"]["maxLength"] == 64
    assert "user_id" not in fields
    assert "portfolio_id" not in fields
