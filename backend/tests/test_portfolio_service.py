from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.services import portfolio_service


@pytest.mark.asyncio
async def test_complete_setup_is_atomic_and_creates_opening_snapshot(monkeypatch):
    repo = SimpleNamespace(
        lock_user_for_setup=AsyncMock(),
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
    repo = SimpleNamespace(
        lock_user_for_setup=AsyncMock(),
        get_portfolio=AsyncMock(return_value=SimpleNamespace(id="portfolio-1")),
    )
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


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ItemsResult:
    def __init__(self, items):
        self.items = items

    def scalars(self):
        return SimpleNamespace(all=lambda: self.items)


class RecordingDB:
    def __init__(self, *results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


@pytest.mark.asyncio
async def test_setup_locks_user_before_portfolio_existence_check(monkeypatch):
    calls = []

    async def lock_user(user_id):
        calls.append(("lock", user_id))

    async def get_portfolio(user_id):
        calls.append(("portfolio", user_id))
        return SimpleNamespace(id="portfolio-1")

    repo = SimpleNamespace(
        lock_user_for_setup=lock_user,
        get_portfolio=get_portfolio,
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_service.complete_setup(
            SimpleNamespace(), "00000000-0000-0000-0000-000000000001", SimpleNamespace(), None
        )

    assert exc_info.value.status_code == 409
    assert calls == [
        ("lock", "00000000-0000-0000-0000-000000000001"),
        ("portfolio", "00000000-0000-0000-0000-000000000001"),
    ]


@pytest.mark.asyncio
async def test_setup_lock_query_uses_user_row_for_update():
    db = RecordingDB(ScalarResult(SimpleNamespace(id="user-1")))

    await portfolio_service.PortfolioRepository(db).lock_user_for_setup("user-1")

    statement = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "FROM users" in statement
    assert "FOR UPDATE" in statement
    assert "users.id" in statement


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stocks", "symbol"),
    [([], "000001"), ([SimpleNamespace(symbol="000001", in_csi300=False)], "000001")],
)
async def test_validate_symbols_rejects_missing_or_non_csi300_stock(stocks, symbol):
    db = RecordingDB(ItemsResult(stocks))

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_service.validate_symbols(db, [symbol])

    assert exc_info.value.status_code == 422
    assert symbol in exc_info.value.detail


@pytest.mark.asyncio
async def test_valuation_uses_latest_bar_on_or_before_today_and_capital_tolerance():
    latest_date = date.today() - timedelta(days=1)
    db = RecordingDB(
        ItemsResult([SimpleNamespace(symbol="000001", name="平安银行", industry="金融")]),
        ScalarResult(SimpleNamespace(close=Decimal("11"), trade_date=latest_date)),
    )
    position = SimpleNamespace(symbol="000001", quantity=10, average_cost=Decimal("10"))
    payload = SimpleNamespace(
        positions=[position], cash=Decimal("900"), total_capital=Decimal("1110")
    )

    await portfolio_service.validate_declared_capital(db, payload)

    assert "daily_bars.trade_date <=" in str(db.statements[1])
    assert "DESC" in str(db.statements[1])


@pytest.mark.asyncio
async def test_capital_mismatch_includes_server_valuation():
    db = RecordingDB(
        ItemsResult([SimpleNamespace(symbol="000001", name="平安银行", industry="金融")]),
        ScalarResult(SimpleNamespace(close=Decimal("11"), trade_date=date.today())),
    )
    payload = SimpleNamespace(
        positions=[SimpleNamespace(symbol="000001", quantity=10, average_cost=Decimal("10"))],
        cash=Decimal("900"),
        total_capital=Decimal("1111"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_service.validate_declared_capital(db, payload)

    assert exc_info.value.status_code == 422
    assert "1010" in exc_info.value.detail


@pytest.mark.asyncio
async def test_valuation_falls_back_to_average_cost_when_no_bar_exists():
    db = RecordingDB(
        ItemsResult([SimpleNamespace(symbol="000001", name="平安银行", industry="金融")]),
        ScalarResult(None),
    )

    values = await portfolio_service.value_positions(
        db, [SimpleNamespace(symbol="000001", quantity=10, average_cost=Decimal("10.25"))]
    )

    assert values[0].latest_close == Decimal("10.25")
    assert values[0].price_date is None
    assert values[0].market_value == Decimal("102.50")
    assert values[0].valuation_warning == "000001缺少最新行情，已按成本价估值"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "constraint_message",
    [
        "UNIQUE constraint failed: portfolios.user_id",
        "UNIQUE constraint failed: investment_profiles.user_id, investment_profiles.version",
    ],
)
async def test_relevant_setup_integrity_error_becomes_409(monkeypatch, constraint_message):
    repo = SimpleNamespace(
        lock_user_for_setup=AsyncMock(),
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
    monkeypatch.setattr(
        portfolio_service,
        "log_action",
        AsyncMock(
            side_effect=IntegrityError(
                "insert", {}, Exception(constraint_message)
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_service.complete_setup(
            SimpleNamespace(flush=AsyncMock()),
            "00000000-0000-0000-0000-000000000001",
            SimpleNamespace(profile=SimpleNamespace(), cash=Decimal("100"), positions=[]),
            None,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "投资组合已经初始化"


def test_unrelated_integrity_error_is_not_mapped_to_setup_conflict():
    error = IntegrityError("insert", {}, Exception("NOT NULL constraint failed: portfolios.cash"))

    assert portfolio_service.is_setup_duplicate_integrity_error(error) is False


@pytest.mark.asyncio
async def test_setup_failure_propagates_without_service_commit_or_partial_response(monkeypatch):
    repo = SimpleNamespace(
        lock_user_for_setup=AsyncMock(),
        get_portfolio=AsyncMock(return_value=None),
        create_profile=AsyncMock(return_value=SimpleNamespace(id="profile-1", version=1)),
        create_portfolio=AsyncMock(side_effect=RuntimeError("write failed")),
        portfolio_response=AsyncMock(),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    monkeypatch.setattr(portfolio_service, "validate_symbols", AsyncMock())
    monkeypatch.setattr(portfolio_service, "validate_declared_capital", AsyncMock())
    db = SimpleNamespace(commit=AsyncMock(), flush=AsyncMock())
    payload = SimpleNamespace(profile=SimpleNamespace(), cash=Decimal("100"), positions=[])

    with pytest.raises(RuntimeError, match="write failed"):
        await portfolio_service.complete_setup(db, "user-1", payload, None)

    db.commit.assert_not_awaited()
    db.flush.assert_not_awaited()
    repo.portfolio_response.assert_not_awaited()
