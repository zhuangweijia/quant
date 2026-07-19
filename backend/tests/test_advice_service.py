from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import advice_service

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
SIGNAL_DATE = date(2026, 7, 17)


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class RowsResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


def engine_result(*, violations=()):
    return SimpleNamespace(
        current_exposure=Decimal("0.2"),
        target_exposure=Decimal("0.3"),
        estimated_cash=Decimal("7000"),
        total_asset=Decimal("10000"),
        historical_max_drawdown=Decimal("0.05"),
        turnover=Decimal("0.1"),
        constraint_violations=violations,
        lines=(),
    )


def advice_inputs(*, input_error_code=None):
    profile = SimpleNamespace(
        id="profile-1",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.10"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )
    portfolio = SimpleNamespace(
        id="portfolio-1",
        cash=Decimal("8000"),
        updated_at=datetime(2026, 7, 17, 8, tzinfo=UTC),
    )
    return advice_service.AdviceInputs(
        user_id=USER_ID,
        profile=profile,
        portfolio=portfolio,
        positions=(),
        engine_profile=SimpleNamespace(),
        engine_positions=(),
        engine_candidates=(),
        snapshot_positions=(),
        model_version="model-v1",
        data_date=SIGNAL_DATE,
        input_error_code=input_error_code,
    )


@pytest.mark.asyncio
async def test_generation_is_idempotent_without_force(monkeypatch):
    existing = SimpleNamespace(id="advice-1", status="ready")
    repo = SimpleNamespace(find_current=AsyncMock(return_value=existing))
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)

    result = await advice_service.generate_for_user(
        SimpleNamespace(), "user-1", SIGNAL_DATE
    )

    assert result is existing


@pytest.mark.asyncio
async def test_generation_rejects_incomplete_portfolio(monkeypatch):
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=None),
        lock_versions=AsyncMock(return_value=[]),
        load_inputs=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)

    with pytest.raises(HTTPException) as exc:
        await advice_service.generate_for_user(SimpleNamespace(), "user-1", SIGNAL_DATE)

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "portfolio_setup_required"


@pytest.mark.asyncio
async def test_newer_market_session_expires_unresolved_advice(monkeypatch):
    advice = SimpleNamespace(signal_date=SIGNAL_DATE, status="ready")
    repo = SimpleNamespace(
        latest_market_date=AsyncMock(return_value=date(2026, 7, 18)),
        expire=AsyncMock(),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)

    await advice_service.expire_if_needed(SimpleNamespace(), advice)

    repo.expire.assert_awaited_once_with(advice)


@pytest.mark.asyncio
async def test_force_generation_creates_next_version(monkeypatch):
    events = []
    prior = SimpleNamespace(id="advice-1", version=1, status="ready")
    replacement = SimpleNamespace(id="advice-2", version=2, status="ready")
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=prior),
        lock_versions=AsyncMock(return_value=[prior]),
        load_inputs=AsyncMock(return_value=advice_inputs()),
        holdings_are_stale=AsyncMock(return_value=False),
        create_snapshot=AsyncMock(return_value=SimpleNamespace(id="snapshot-2")),
        persist_result=AsyncMock(
            side_effect=lambda *args, **kwargs: events.append(
                f"persist:{kwargs['version']}"
            )
            or replacement
        ),
        flush=AsyncMock(side_effect=lambda: events.append("flush")),
        supersede=AsyncMock(side_effect=lambda *args: events.append("supersede")),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    monkeypatch.setattr(advice_service, "build_advice", lambda *args, **kwargs: engine_result())

    result = await advice_service.generate_for_user(
        SimpleNamespace(), USER_ID, SIGNAL_DATE, force=True
    )

    assert result is replacement
    assert replacement.version == 2
    assert events == ["persist:2", "flush", "supersede"]
    repo.supersede.assert_awaited_once_with(prior, replacement)


@pytest.mark.asyncio
async def test_failed_replacement_keeps_prior_current(monkeypatch):
    prior = SimpleNamespace(id="advice-1", version=3, status="ready", superseded_by_id=None)
    failed = SimpleNamespace(id="advice-2", version=4, status="failed")
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=prior),
        lock_versions=AsyncMock(return_value=[prior]),
        load_inputs=AsyncMock(return_value=advice_inputs()),
        holdings_are_stale=AsyncMock(return_value=False),
        create_snapshot=AsyncMock(return_value=SimpleNamespace(id="snapshot-2")),
        persist_failure=AsyncMock(return_value=failed),
        flush=AsyncMock(),
        supersede=AsyncMock(),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    monkeypatch.setattr(
        advice_service, "build_advice", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError())
    )

    result = await advice_service.generate_for_user(
        SimpleNamespace(), USER_ID, SIGNAL_DATE, force=True
    )

    assert result is failed
    assert prior.status == "ready"
    assert prior.superseded_by_id is None
    repo.supersede.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_continues_after_one_user_failure(monkeypatch):
    monkeypatch.setattr(
        advice_service,
        "_list_active_user_ids",
        AsyncMock(return_value=["user-1", "user-2"]),
    )
    generate = AsyncMock(
        side_effect=[
            SimpleNamespace(id="advice-1", status="ready"),
            HTTPException(status_code=409, detail={"code": "portfolio_setup_required"}),
        ]
    )
    monkeypatch.setattr(advice_service, "_generate_and_publish", generate)

    summary = await advice_service.generate_for_all_users(SIGNAL_DATE)

    assert summary == {
        "signal_date": "2026-07-17",
        "succeeded": [{"user_id": "user-1", "advice_id": "advice-1"}],
        "failed": [{"user_id": "user-2", "error_code": "portfolio_setup_required"}],
    }
    assert generate.await_count == 2


@pytest.mark.asyncio
async def test_missing_held_symbol_data_persists_failed_without_items(monkeypatch):
    failed = SimpleNamespace(id="failed-1", version=1, status="failed")
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=None),
        lock_versions=AsyncMock(return_value=[]),
        load_inputs=AsyncMock(return_value=advice_inputs(input_error_code="held_market_data_missing")),
        holdings_are_stale=AsyncMock(return_value=False),
        create_snapshot=AsyncMock(return_value=SimpleNamespace(id="snapshot-1")),
        persist_failure=AsyncMock(return_value=failed),
        flush=AsyncMock(),
        count_items=AsyncMock(return_value=0),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)

    result = await advice_service.generate_for_user(SimpleNamespace(), USER_ID, SIGNAL_DATE)

    assert result.status == "failed"
    assert await repo.count_items(result.id) == 0
    assert repo.persist_failure.await_args.kwargs["error_code"] == "held_market_data_missing"


@pytest.mark.asyncio
async def test_progressive_constraint_codes_are_persisted_in_engine_order(monkeypatch):
    persisted = SimpleNamespace(id="advice-1", version=1, status="ready")
    violations = (
        "cash_below_minimum",
        "stock_cap_exceeded:000001",
        "industry_cap_exceeded:unknown",
    )
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=None),
        lock_versions=AsyncMock(return_value=[]),
        load_inputs=AsyncMock(return_value=advice_inputs()),
        holdings_are_stale=AsyncMock(return_value=False),
        create_snapshot=AsyncMock(return_value=SimpleNamespace(id="snapshot-1")),
        persist_result=AsyncMock(return_value=persisted),
        flush=AsyncMock(),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    monkeypatch.setattr(
        advice_service,
        "build_advice",
        lambda *args, **kwargs: engine_result(violations=violations),
    )

    await advice_service.generate_for_user(SimpleNamespace(), USER_ID, SIGNAL_DATE)

    result = repo.persist_result.await_args.kwargs["result"]
    assert result.constraint_violations == violations


@pytest.mark.asyncio
async def test_stale_pending_holdings_persist_failed_advice(monkeypatch):
    failed = SimpleNamespace(id="failed-1", version=1, status="failed")
    repo = SimpleNamespace(
        find_current=AsyncMock(return_value=None),
        lock_versions=AsyncMock(return_value=[]),
        load_inputs=AsyncMock(return_value=advice_inputs()),
        holdings_are_stale=AsyncMock(return_value=True),
        create_snapshot=AsyncMock(return_value=SimpleNamespace(id="snapshot-1")),
        persist_failure=AsyncMock(return_value=failed),
        flush=AsyncMock(),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)

    result = await advice_service.generate_for_user(SimpleNamespace(), USER_ID, SIGNAL_DATE)

    assert result.status == "failed"
    assert repo.persist_failure.await_args.kwargs["error_code"] == "holdings_stale"


@pytest.mark.asyncio
async def test_repository_loads_user_scoped_inputs_in_batched_queries():
    profile = SimpleNamespace(
        id="profile-1",
        max_drawdown=Decimal("0.15"),
        max_stock_weight=Decimal("0.10"),
        max_industry_weight=Decimal("0.25"),
        min_cash_ratio=Decimal("0.10"),
        max_daily_turnover=Decimal("0.30"),
    )
    portfolio = SimpleNamespace(id="portfolio-1", cash=Decimal("8000"))
    positions = [SimpleNamespace(symbol="000001", quantity=100, total_cost=Decimal("900"))]
    predictions = [
        SimpleNamespace(
            symbol="000001", score=Decimal("0.8"), rank=1, confidence="high",
            model_version="model-v1",
            explanation={"positive": ["盈利改善"], "negative": ["估值偏高"]},
        ),
        SimpleNamespace(
            symbol="000002", score=Decimal("0.7"), rank=2, confidence="normal",
            model_version="model-v1", explanation=None,
        ),
    ]
    stocks = [
        SimpleNamespace(symbol="000001", name="平安银行", industry="银行"),
        SimpleNamespace(symbol="000002", name="万科A", industry="地产"),
    ]
    closes = [
        SimpleNamespace(symbol="000001", close=Decimal("10"), trade_date=SIGNAL_DATE),
        SimpleNamespace(symbol="000002", close=Decimal("20"), trade_date=SIGNAL_DATE),
    ]
    history = []
    for offset in range(61):
        trade_date = SIGNAL_DATE - timedelta(days=60 - offset)
        history.extend(
            [
                ("000001", trade_date, Decimal(10 + offset) / Decimal("10")),
                ("000002", trade_date, Decimal(20 + 2 * offset) / Decimal("10")),
            ]
        )
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                ScalarResult(profile),
                ScalarResult(portfolio),
                ScalarsResult(positions),
                ScalarsResult(predictions),
                ScalarsResult(stocks),
                ScalarsResult(closes),
                RowsResult(history),
            ]
        )
    )

    loaded = await advice_service.AdviceRepository(db).load_inputs(USER_ID, SIGNAL_DATE)

    assert db.execute.await_count == 7
    assert "investment_profiles.user_id" in str(db.execute.await_args_list[0].args[0])
    assert "portfolios.user_id" in str(db.execute.await_args_list[1].args[0])
    assert "stocks.in_csi300 IS true" in str(db.execute.await_args_list[4].args[0])
    assert loaded.model_version == "model-v1"
    assert loaded.engine_positions[0].market_value == Decimal("1000")
    assert loaded.engine_candidates[0].positive_factors == ("盈利改善",)
    assert loaded.engine_candidates[0].risks == ("估值偏高",)
    assert len(loaded.engine_candidates[0].returns) == 60
    assert loaded.engine_candidates[0].returns == loaded.engine_candidates[1].returns


@pytest.mark.asyncio
async def test_repository_rejects_mixed_prediction_model_versions():
    profile = SimpleNamespace(id="profile-1")
    portfolio = SimpleNamespace(id="portfolio-1")
    predictions = [
        SimpleNamespace(model_version="model-v1"),
        SimpleNamespace(model_version="model-v2"),
    ]
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                ScalarResult(profile),
                ScalarResult(portfolio),
                ScalarsResult([]),
                ScalarsResult(predictions),
            ]
        )
    )

    with pytest.raises(advice_service.AdviceInputError) as exc:
        await advice_service.AdviceRepository(db).load_inputs(USER_ID, SIGNAL_DATE)

    assert exc.value.code == "mixed_model_versions"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("generating", "generating"),
        ("ready", "ready"),
        ("partially_handled", "partially_handled"),
        ("handled", "handled"),
        ("expired", "expired"),
        ("failed", "failed"),
    ],
)
async def test_today_returns_every_persisted_business_state(monkeypatch, status, expected):
    advice = SimpleNamespace(
        status=status,
        error_code="engine_failed" if status == "failed" else None,
        error_message="建议生成失败" if status == "failed" else None,
    )
    response = advice_service.DailyAdviceResponse.model_construct(status=status)
    repo = SimpleNamespace(
        find_latest=AsyncMock(return_value=advice),
        to_response=AsyncMock(return_value=response),
        setup_complete=AsyncMock(return_value=True),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    monkeypatch.setattr(advice_service, "expire_stale_advice", AsyncMock())

    today = await advice_service.get_today_state(SimpleNamespace(), USER_ID)

    assert today.state == expected
    assert today.advice is response


@pytest.mark.asyncio
async def test_today_distinguishes_not_generated_from_setup_required(monkeypatch):
    repo = SimpleNamespace(
        find_latest=AsyncMock(return_value=None),
        setup_complete=AsyncMock(side_effect=[True, False]),
    )
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    monkeypatch.setattr(advice_service, "expire_stale_advice", AsyncMock())

    complete = await advice_service.get_today_state(SimpleNamespace(), USER_ID)
    incomplete = await advice_service.get_today_state(SimpleNamespace(), USER_ID)

    assert complete.state == "not_generated" and complete.setup_required is False
    assert incomplete.state == "not_generated" and incomplete.setup_required is True


@pytest.mark.asyncio
async def test_batch_commits_before_publishing_targeted_event(monkeypatch):
    events = []
    advice = SimpleNamespace(id="advice-1", signal_date=SIGNAL_DATE, status="ready")
    db = SimpleNamespace(
        commit=AsyncMock(side_effect=lambda: events.append("commit")),
        rollback=AsyncMock(),
    )

    class SessionContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(advice_service, "AsyncSessionLocal", lambda: SessionContext())
    monkeypatch.setattr(advice_service, "generate_for_user", AsyncMock(return_value=advice))
    monkeypatch.setattr(
        advice_service.event_bus,
        "publish",
        AsyncMock(side_effect=lambda *args: events.append("publish")),
    )

    result = await advice_service._generate_and_publish("user-1", SIGNAL_DATE)

    assert result is advice
    assert events == ["commit", "publish"]
    advice_service.event_bus.publish.assert_awaited_once_with(
        advice_service.event_bus.TOPIC_ADVICE_READY,
        {"user_id": "user-1", "advice_id": "advice-1", "signal_date": "2026-07-17"},
    )


@pytest.mark.asyncio
async def test_batch_enumeration_preserves_uuid_values_for_typed_queries(monkeypatch):
    db = SimpleNamespace(execute=AsyncMock(return_value=ScalarsResult([USER_ID])))

    class SessionContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(advice_service, "AsyncSessionLocal", lambda: SessionContext())

    user_ids = await advice_service._list_active_user_ids()

    assert user_ids == [USER_ID]
