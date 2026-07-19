from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services import portfolio_service


@pytest.mark.asyncio
async def test_complete_setup_is_atomic_and_creates_opening_snapshot(monkeypatch):
    repo = SimpleNamespace(
        get_portfolio=AsyncMock(return_value=None),
        create_profile=AsyncMock(return_value=SimpleNamespace(id="profile-1", version=1)),
        create_portfolio=AsyncMock(return_value=SimpleNamespace(id="portfolio-1")),
        replace_positions=AsyncMock(),
        create_opening_events=AsyncMock(),
        create_snapshot=AsyncMock(),
        portfolio_response=AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    monkeypatch.setattr(portfolio_service, "validate_symbols", AsyncMock())
    monkeypatch.setattr(portfolio_service, "validate_declared_capital", AsyncMock())
    monkeypatch.setattr(portfolio_service, "log_action", AsyncMock())
    db = SimpleNamespace(flush=AsyncMock())
    payload = SimpleNamespace(profile=SimpleNamespace(), cash=Decimal("9000"), positions=[])

    await portfolio_service.complete_setup(
        db, "00000000-0000-0000-0000-000000000001", payload, ("127.0.0.1", "test")
    )

    repo.create_profile.assert_awaited_once_with(
        "00000000-0000-0000-0000-000000000001", 1, payload.profile
    )
    repo.create_portfolio.assert_awaited_once_with(
        "00000000-0000-0000-0000-000000000001", payload.cash
    )
    repo.replace_positions.assert_awaited_once_with("portfolio-1", payload.positions)
    repo.create_opening_events.assert_awaited_once_with(
        "portfolio-1", payload.cash, payload.positions
    )
    repo.create_snapshot.assert_awaited_once_with("portfolio-1", "setup", "profile", "profile-1")
    repo.portfolio_response.assert_awaited_once_with("00000000-0000-0000-0000-000000000001")
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_second_setup_returns_409(monkeypatch):
    repo = SimpleNamespace(get_portfolio=AsyncMock(return_value=SimpleNamespace(id="portfolio-1")))
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_service.complete_setup(
            SimpleNamespace(), "00000000-0000-0000-0000-000000000001", SimpleNamespace(), None
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "投资组合已经初始化"


@pytest.mark.asyncio
async def test_profile_update_creates_version_two(monkeypatch):
    active = SimpleNamespace(
        id="profile-1",
        version=1,
        investment_horizon_days=120,
        risk_level="balanced",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.08"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )
    replacement = SimpleNamespace(id="profile-2", version=2)
    repo = SimpleNamespace(
        get_active_profile_for_update=AsyncMock(return_value=active),
        deactivate_profile=AsyncMock(),
        create_profile=AsyncMock(return_value=replacement),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    monkeypatch.setattr(portfolio_service, "log_action", AsyncMock())
    db = SimpleNamespace(flush=AsyncMock())
    payload = SimpleNamespace(
        investment_horizon_days=240,
        risk_level="balanced",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.08"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )

    response = await portfolio_service.create_profile_version(
        db, "00000000-0000-0000-0000-000000000001", payload, None
    )

    repo.deactivate_profile.assert_awaited_once_with(active)
    repo.create_profile.assert_awaited_once_with(
        "00000000-0000-0000-0000-000000000001", 2, payload
    )
    assert response is replacement
    assert response.version == 2
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_status_reports_missing_profile_and_portfolio(monkeypatch):
    repo = SimpleNamespace(
        get_active_profile=AsyncMock(return_value=None),
        get_portfolio=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)

    status = await portfolio_service.get_setup_status(
        SimpleNamespace(), "00000000-0000-0000-0000-000000000001"
    )

    assert status.complete is False
    assert status.has_profile is False
    assert status.has_portfolio is False
    assert status.missing == ["profile", "portfolio"]


@pytest.mark.asyncio
async def test_setup_queries_are_user_scoped(monkeypatch):
    user_id = "00000000-0000-0000-0000-000000000001"
    repo = SimpleNamespace(
        get_active_profile=AsyncMock(return_value=SimpleNamespace()),
        get_portfolio=AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)

    await portfolio_service.get_setup_status(SimpleNamespace(), user_id)

    repo.get_active_profile.assert_awaited_once_with(user_id)
    repo.get_portfolio.assert_awaited_once_with(user_id)
