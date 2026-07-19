from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1 import portfolio as portfolio_api
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
