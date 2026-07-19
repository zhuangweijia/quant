from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app import database
from app.models.advice import AdviceItem, DailyAdvice
from app.models.audit_log import AuditLog
from app.models.daily_bar import DailyBar
from app.models.execution import ExecutionMutation, ExecutionRecord
from app.models.portfolio import Portfolio, PortfolioEvent, PortfolioSnapshot, Position
from app.models.stock import Stock
from app.schemas.advice import ExecutionUpdateRequest
from app.services import execution_service

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 7, 19, 9, tzinfo=UTC)
SIGNAL_DATE = date(2026, 7, 18)


@compiles(postgresql.JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = (
        Portfolio.__table__,
        Position.__table__,
        PortfolioEvent.__table__,
        PortfolioSnapshot.__table__,
        DailyAdvice.__table__,
        AdviceItem.__table__,
        ExecutionRecord.__table__,
        ExecutionMutation.__table__,
        DailyBar.__table__,
        Stock.__table__,
        AuditLog.__table__,
    )
    async with engine.begin() as connection:
        for table in tables:
            await connection.run_sync(lambda sync, selected=table: selected.create(sync))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def seed_advice(
    db,
    *,
    user_id=USER_ID,
    action="buy",
    delta_quantity=100,
    cash=Decimal("2000"),
    position_quantity=0,
    position_total_cost=Decimal("0"),
    advice_status="ready",
    item_status="pending",
):
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        currency="CNY",
        cash=cash,
        last_confirmed_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    snapshot = PortfolioSnapshot(
        id=uuid4(),
        portfolio_id=portfolio.id,
        reason="advice_generation",
        reference_type="daily_advice",
        reference_id="seed",
        cash=cash,
        market_value=position_total_cost,
        total_asset=cash + position_total_cost,
        price_date=SIGNAL_DATE,
        positions=[],
        captured_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    advice = DailyAdvice(
        id=uuid4(),
        user_id=user_id,
        portfolio_id=portfolio.id,
        profile_id=uuid4(),
        source_snapshot_id=snapshot.id,
        signal_date=SIGNAL_DATE,
        version=1,
        status=advice_status,
        model_version="model-v1",
        data_date=SIGNAL_DATE,
        current_exposure=Decimal("0"),
        target_exposure=Decimal("0.5"),
        estimated_cash=Decimal("1000"),
        constraint_violations=[],
        generated_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    item = AdviceItem(
        id=uuid4(),
        advice_id=advice.id,
        symbol="000001",
        name="平安银行",
        industry="银行",
        action=action,
        status=item_status,
        current_quantity=position_quantity,
        target_quantity=position_quantity + delta_quantity,
        delta_quantity=delta_quantity,
        current_weight=Decimal("0"),
        target_weight=Decimal("0.5"),
        reference_price=Decimal("10"),
        price_tolerance=Decimal("0.03"),
        score=Decimal("0.8"),
        rank=1,
        confidence="high",
        positive_factors=["盈利改善"],
        risks=["估值偏高"],
        invalidation_conditions=["价格偏离"],
        constraint_notes=[],
        created_at=NOW,
        updated_at=NOW,
    )
    db.add_all([portfolio, snapshot, advice, item])
    if position_quantity:
        db.add(
            Position(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol=item.symbol,
                quantity=position_quantity,
                total_cost=position_total_cost,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    await db.flush()
    return portfolio, advice, item


def payload(
    disposition="executed",
    *,
    quantity=100,
    price=Decimal("10"),
    fee=Decimal("5"),
    expected_revision=0,
    acknowledge=False,
):
    if disposition == "skipped":
        return ExecutionUpdateRequest(
            disposition="skipped",
            reason="本次不执行",
            expected_revision=expected_revision,
        )
    return ExecutionUpdateRequest(
        disposition=disposition,
        quantity=quantity,
        price=price,
        fee=fee,
        executed_at=NOW,
        expected_revision=expected_revision,
        acknowledge_outside_advice=acknowledge,
    )


async def count_rows(db, model):
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def run_get_db_request(operation):
    generator = database.get_db()
    db = await anext(generator)
    try:
        result = await operation(db)
    except BaseException as error:
        try:
            await generator.athrow(error)
        except BaseException as reraised:
            raise reraised
        raise AssertionError("get_db swallowed the request exception")
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    return result


def test_owner_lock_sql_scopes_user_and_uses_for_update():
    statement = execution_service._owned_item_lock_statement(USER_ID, uuid4())
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "daily_advices.user_id" in sql
    assert "FOR UPDATE OF daily_advices" in sql


@pytest.mark.parametrize("code_attribute", ["sqlstate", "pgcode"])
def test_asyncpg_wrapped_target_unique_violation_is_mapped_by_exact_constraint(
    code_attribute,
):
    driver = Exception(
        'duplicate key value violates unique constraint "uq_execution_mutation_key"'
    )
    middle = Exception("asyncpg driver wrapper")
    middle.__context__ = driver
    outer = Exception("SQLAlchemy asyncpg adapter wrapper")
    setattr(outer, code_attribute, "23505")
    outer.__cause__ = middle
    error = IntegrityError("insert", {}, outer)

    assert execution_service._is_idempotency_conflict(error) is True


@pytest.mark.parametrize(
    ("code", "constraint"),
    [
        ("23505", "uq_execution_item"),
        ("23503", "uq_execution_mutation_key"),
    ],
)
def test_other_postgres_integrity_errors_are_not_mapped_to_idempotency_conflict(
    code,
    constraint,
):
    wrapped = Exception(f'duplicate key value violates unique constraint "{constraint}"')
    wrapped.sqlstate = code
    error = IntegrityError("insert", {}, wrapped)

    assert execution_service._is_idempotency_conflict(error) is False


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_existing_result_without_second_delta(
    session_factory,
):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db)
        first = await execution_service.update_execution(
            db, USER_ID, item.id, payload(), "same-key", ("127.0.0.1", "pytest")
        )
        replay = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(price=Decimal("99")),
            "same-key",
            ("127.0.0.1", "pytest"),
        )

        await db.refresh(portfolio)
        position = await db.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
        assert replay == first
        assert portfolio.cash == Decimal("995")
        assert (position.quantity, position.total_cost) == (100, Decimal("1005"))
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1
        assert await count_rows(db, PortfolioSnapshot) == 3


@pytest.mark.asyncio
async def test_same_idempotency_key_from_another_user_returns_conflict_without_leak(
    session_factory,
):
    async with session_factory() as db:
        first_portfolio, _first_advice, first_item = await seed_advice(db)
        second_portfolio, _second_advice, second_item = await seed_advice(
            db, user_id=OTHER_USER_ID
        )
        await execution_service.update_execution(
            db, USER_ID, first_item.id, payload(), "shared-key", None
        )

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, OTHER_USER_ID, second_item.id, payload(), "shared-key", None
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "idempotency_key_conflict"
        assert first_portfolio.cash == Decimal("995")
        assert second_portfolio.cash == Decimal("2000")
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1


@pytest.mark.asyncio
async def test_flush_race_409_rolls_back_request_transaction_without_partial_state(
    session_factory,
    monkeypatch,
):
    async with session_factory() as setup_db:
        portfolio, advice, item = await seed_advice(setup_db)
        portfolio_id = portfolio.id
        advice_id = advice.id
        item_id = item.id
        await setup_db.commit()

    original_log_action = execution_service.log_action

    async def flush_with_duplicate_mutation(db, **kwargs):
        pending = next(entity for entity in db.new if isinstance(entity, ExecutionMutation))
        db.add(
            ExecutionMutation(
                id=uuid4(),
                execution_id=pending.execution_id,
                idempotency_key=pending.idempotency_key,
                revision=pending.revision + 1,
                before_state=pending.before_state,
                after_state=pending.after_state,
                portfolio_event_ids=pending.portfolio_event_ids,
                created_at=pending.created_at,
                updated_at=pending.updated_at,
            )
        )
        await original_log_action(db, **kwargs)

    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(execution_service, "log_action", flush_with_duplicate_mutation)

    async def request(db):
        return await execution_service.update_execution(
            db, USER_ID, item_id, payload(), "flush-race-key", None
        )

    with pytest.raises(HTTPException) as exc:
        await run_get_db_request(request)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "idempotency_key_conflict"

    async with session_factory() as verification_db:
        stored_portfolio = await verification_db.get(Portfolio, portfolio_id)
        stored_advice = await verification_db.get(DailyAdvice, advice_id)
        stored_item = await verification_db.get(AdviceItem, item_id)
        assert stored_portfolio.cash == Decimal("2000")
        assert stored_advice.status == "ready"
        assert stored_item.status == "pending"
        assert await count_rows(verification_db, Position) == 0
        assert await count_rows(verification_db, ExecutionRecord) == 0
        assert await count_rows(verification_db, ExecutionMutation) == 0
        assert await count_rows(verification_db, PortfolioEvent) == 0
        assert await count_rows(verification_db, AuditLog) == 0
        assert await count_rows(verification_db, PortfolioSnapshot) == 1


@pytest.mark.asyncio
async def test_buy_cannot_overdraw_cash_and_appends_nothing(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("100"))
        initial_snapshots = await count_rows(db, PortfolioSnapshot)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(), "overdraw", None
            )

        assert exc.value.status_code == 422
        assert portfolio.cash == Decimal("100")
        assert await count_rows(db, Position) == 0
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots


@pytest.mark.asyncio
async def test_sell_quantity_cannot_exceed_available_position_and_appends_nothing(
    session_factory,
):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(
            db,
            action="exit",
            delta_quantity=-100,
            position_quantity=100,
            position_total_cost=Decimal("800"),
        )
        initial_snapshots = await count_rows(db, PortfolioSnapshot)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(quantity=200), "oversell", None
            )

        position = await db.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
        assert exc.value.status_code == 422
        assert portfolio.cash == Decimal("2000")
        assert (position.quantity, position.total_cost) == (100, Decimal("800"))
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots

        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(quantity=100, expected_revision=0),
            "valid-exit",
            None,
        )
        assert response.item.execution.revision == 1
        assert portfolio.cash == Decimal("2995")
        assert await count_rows(db, Position) == 0
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots + 2


@pytest.mark.asyncio
async def test_partial_status_updates_delta_and_append_only_records(session_factory):
    async with session_factory() as db:
        portfolio, advice, item = await seed_advice(db)

        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload("partial", quantity=40, fee=Decimal("1")),
            "partial-key",
            None,
        )

        position = await db.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
        event = await db.scalar(select(PortfolioEvent))
        assert portfolio.cash == Decimal("1599")
        assert (position.quantity, position.total_cost) == (40, Decimal("401"))
        assert (item.status, advice.status, response.advice_state) == (
            "partial",
            "partially_handled",
            "partially_handled",
        )
        assert (event.quantity_delta, event.cash_delta) == (40, Decimal("-401"))
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1
        assert await count_rows(db, PortfolioSnapshot) == 3


@pytest.mark.asyncio
async def test_price_band_requires_acknowledgement_before_mutation(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("3000"))
        initial_snapshots = await count_rows(db, PortfolioSnapshot)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db,
                USER_ID,
                item.id,
                payload(price=Decimal("11"), fee=Decimal("0")),
                "outside-1",
                None,
            )
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "outside_advice_requires_acknowledgement"
        assert portfolio.cash == Decimal("3000")
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots

        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(price=Decimal("11"), fee=Decimal("0"), acknowledge=True),
            "outside-2",
            None,
        )
        assert portfolio.cash == Decimal("1900")
        assert response.item.execution.within_price_band is False
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots + 2


@pytest.mark.asyncio
async def test_expired_advice_requires_acknowledgement_before_mutation(session_factory):
    async with session_factory() as db:
        portfolio, advice, item = await seed_advice(db)
        db.add(
            DailyBar(
                id=1,
                symbol=item.symbol,
                trade_date=SIGNAL_DATE + timedelta(days=1),
                open=Decimal("10"),
                high=Decimal("10"),
                low=Decimal("10"),
                close=Decimal("10"),
                volume=Decimal("1"),
            )
        )
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(fee=Decimal("0")), "expired-1", None
            )
        assert exc.value.status_code == 409
        assert advice.status == "ready"
        assert portfolio.cash == Decimal("2000")
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0

        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(fee=Decimal("0"), acknowledge=True),
            "expired-2",
            None,
        )
        assert portfolio.cash == Decimal("1000")
        assert response.item.execution.within_price_band is False
        assert advice.status == "expired"
        assert await count_rows(db, ExecutionMutation) == 1
        assert await count_rows(db, PortfolioEvent) == 1


@pytest.mark.asyncio
async def test_persisted_expired_status_also_requires_acknowledgement(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, advice_status="expired")

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(fee=Decimal("0")), "persisted-expired", None
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "outside_advice_requires_acknowledgement"
        assert portfolio.cash == Decimal("2000")
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0


@pytest.mark.asyncio
async def test_superseded_advice_cannot_mutate_portfolio_or_append_execution(session_factory):
    async with session_factory() as db:
        portfolio, advice, item = await seed_advice(db, advice_status="superseded")
        advice.superseded_by_id = uuid4()
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(), "superseded-key", None
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "advice_superseded"
        assert portfolio.cash == Decimal("2000")
        assert advice.status == "superseded"
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0


@pytest.mark.asyncio
async def test_stale_revision_returns_409_without_delta_or_append(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db)
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(), "revision-1", None
        )
        cash_after_first = portfolio.cash
        events_after_first = await count_rows(db, PortfolioEvent)
        mutations_after_first = await count_rows(db, ExecutionMutation)
        snapshots_after_first = await count_rows(db, PortfolioSnapshot)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db,
                USER_ID,
                item.id,
                payload(price=Decimal("10.1"), expected_revision=0),
                "revision-2",
                None,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "stale_execution_revision"
        assert portfolio.cash == cash_after_first
        assert await count_rows(db, PortfolioEvent) == events_after_first
        assert await count_rows(db, ExecutionMutation) == mutations_after_first
        assert await count_rows(db, PortfolioSnapshot) == snapshots_after_first


@pytest.mark.asyncio
async def test_correction_reverses_old_execution_then_applies_new_delta(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("3000"))
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(fee=Decimal("0")), "correct-1", None
        )
        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(price=Decimal("9.8"), fee=Decimal("2"), expected_revision=1),
            "correct-2",
            None,
        )

        position = await db.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
        events = list((await db.execute(select(PortfolioEvent))).scalars())
        mutations = list(
            (
                await db.execute(
                    select(ExecutionMutation).order_by(ExecutionMutation.revision)
                )
            ).scalars()
        )
        original = next(
            event
            for event in events
            if event.reversal_of_id is None and event.payload["revision"] == 1
        )
        reversal = next(event for event in events if event.reversal_of_id is not None)
        corrected = next(
            event
            for event in events
            if event.reversal_of_id is None and event.payload["revision"] == 2
        )
        assert portfolio.cash == Decimal("2018")
        assert (position.quantity, position.total_cost) == (100, Decimal("982"))
        assert response.item.execution.revision == 2
        assert len(events) == 3
        assert reversal.reversal_of_id == original.id
        assert (reversal.quantity_delta, reversal.cash_delta) == (-100, Decimal("1000"))
        assert (corrected.quantity_delta, corrected.cash_delta) == (100, Decimal("-982"))
        assert [mutation.revision for mutation in mutations] == [1, 2]
        assert len(mutations[1].portfolio_event_ids) == 2
        assert await count_rows(db, PortfolioSnapshot) == 5


@pytest.mark.asyncio
async def test_correction_after_skipped_does_not_reverse_an_already_reversed_event(
    session_factory,
):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("3000"))
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(fee=Decimal("0")), "skip-correction-1", None
        )
        await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload("skipped", expected_revision=1),
            "skip-correction-2",
            None,
        )
        response = await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(fee=Decimal("0"), expected_revision=2),
            "skip-correction-3",
            None,
        )

        position = await db.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
        events = list((await db.execute(select(PortfolioEvent))).scalars())
        assert response.item.execution.revision == 3
        assert portfolio.cash == Decimal("2000")
        assert (position.quantity, position.total_cost) == (100, Decimal("1000"))
        assert len(events) == 3
        assert sum(event.reversal_of_id is not None for event in events) == 1


@pytest.mark.asyncio
async def test_initial_skipped_then_same_timestamp_external_event_blocks_execution(
    session_factory,
):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db)
        await execution_service.update_execution(
            db, USER_ID, item.id, payload("skipped"), "initial-skip-1", None
        )
        record = await db.scalar(
            select(ExecutionRecord).where(ExecutionRecord.advice_item_id == item.id)
        )
        db.add(
            PortfolioEvent(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol=item.symbol,
                event_type="manual_adjustment",
                quantity_delta=0,
                cash_delta=Decimal("0"),
                source_type="manual",
                source_id=None,
                payload=None,
                occurred_at=record.updated_at,
                created_at=record.updated_at,
                updated_at=record.updated_at,
            )
        )
        await db.flush()
        mutation_count = await count_rows(db, ExecutionMutation)
        event_count = await count_rows(db, PortfolioEvent)
        snapshot_count = await count_rows(db, PortfolioSnapshot)
        audit_count = await count_rows(db, AuditLog)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db,
                USER_ID,
                item.id,
                payload(expected_revision=1),
                "initial-skip-2",
                None,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "later_symbol_event_requires_reconcile"
        assert portfolio.cash == Decimal("2000")
        assert await count_rows(db, Position) == 0
        assert await count_rows(db, ExecutionMutation) == mutation_count
        assert await count_rows(db, PortfolioEvent) == event_count
        assert await count_rows(db, PortfolioSnapshot) == snapshot_count
        assert await count_rows(db, AuditLog) == audit_count


@pytest.mark.asyncio
async def test_executed_then_skipped_external_event_blocks_reexecution(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("3000"))
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(fee=Decimal("0")), "skip-external-1", None
        )
        await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload("skipped", expected_revision=1),
            "skip-external-2",
            None,
        )
        record = await db.scalar(
            select(ExecutionRecord).where(ExecutionRecord.advice_item_id == item.id)
        )
        assert (
            await execution_service.ExecutionRepository(db).current_execution_event(record.id)
            is None
        )
        external_time = record.updated_at + timedelta(seconds=1)
        db.add(
            PortfolioEvent(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol=item.symbol,
                event_type="manual_adjustment",
                quantity_delta=0,
                cash_delta=Decimal("0"),
                source_type="manual",
                source_id=None,
                payload=None,
                occurred_at=external_time,
                created_at=external_time,
                updated_at=external_time,
            )
        )
        await db.flush()
        mutation_count = await count_rows(db, ExecutionMutation)
        event_count = await count_rows(db, PortfolioEvent)
        snapshot_count = await count_rows(db, PortfolioSnapshot)
        audit_count = await count_rows(db, AuditLog)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db,
                USER_ID,
                item.id,
                payload(fee=Decimal("0"), expected_revision=2),
                "skip-external-3",
                None,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "later_symbol_event_requires_reconcile"
        assert portfolio.cash == Decimal("3000")
        assert await count_rows(db, Position) == 0
        assert await count_rows(db, ExecutionMutation) == mutation_count
        assert await count_rows(db, PortfolioEvent) == event_count
        assert await count_rows(db, PortfolioSnapshot) == snapshot_count
        assert await count_rows(db, AuditLog) == audit_count


@pytest.mark.asyncio
async def test_later_symbol_event_blocks_correction_with_reconcile_conflict(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, cash=Decimal("3000"))
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(fee=Decimal("0")), "later-1", None
        )
        first_event = await db.scalar(select(PortfolioEvent))
        db.add(
            PortfolioEvent(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol=item.symbol,
                event_type="manual_adjustment",
                quantity_delta=0,
                cash_delta=Decimal("0"),
                source_type="manual",
                source_id=None,
                payload=None,
                occurred_at=first_event.occurred_at + timedelta(seconds=1),
                created_at=first_event.created_at + timedelta(seconds=1),
                updated_at=first_event.updated_at + timedelta(seconds=1),
            )
        )
        await db.flush()
        cash_before = portfolio.cash
        event_count = await count_rows(db, PortfolioEvent)
        mutation_count = await count_rows(db, ExecutionMutation)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db,
                USER_ID,
                item.id,
                payload(price=Decimal("9.8"), expected_revision=1),
                "later-2",
                None,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "later_symbol_event_requires_reconcile"
        assert "核对持仓" in exc.value.detail["message"]
        assert portfolio.cash == cash_before
        assert await count_rows(db, PortfolioEvent) == event_count
        assert await count_rows(db, ExecutionMutation) == mutation_count


@pytest.mark.asyncio
async def test_advice_aggregate_status_tracks_all_item_states_and_appends_each_change(
    session_factory,
):
    async with session_factory() as db:
        portfolio, advice, first = await seed_advice(db)
        second = AdviceItem(
            id=uuid4(),
            advice_id=advice.id,
            symbol="000002",
            name="万科A",
            industry="地产",
            action="buy",
            status="pending",
            current_quantity=0,
            target_quantity=100,
            delta_quantity=100,
            current_weight=Decimal("0"),
            target_weight=Decimal("0.2"),
            reference_price=Decimal("5"),
            price_tolerance=Decimal("0.03"),
            score=Decimal("0.7"),
            rank=2,
            confidence="normal",
            positive_factors=[],
            risks=[],
            invalidation_conditions=[],
            constraint_notes=[],
            created_at=NOW,
            updated_at=NOW,
        )
        db.add(second)
        await db.flush()

        first_response = await execution_service.update_execution(
            db, USER_ID, first.id, payload("skipped"), "aggregate-1", None
        )
        second_response = await execution_service.update_execution(
            db,
            USER_ID,
            second.id,
            payload(quantity=100, price=Decimal("5"), fee=Decimal("0")),
            "aggregate-2",
            None,
        )

        assert first_response.advice_state == "partially_handled"
        assert second_response.advice_state == "handled"
        assert advice.status == "handled"
        assert portfolio.cash == Decimal("1500")
        assert await count_rows(db, Position) == 1
        assert await count_rows(db, ExecutionMutation) == 2
        assert await count_rows(db, PortfolioEvent) == 1
        assert await count_rows(db, PortfolioSnapshot) == 5


@pytest.mark.asyncio
async def test_before_after_snapshots_and_audit_hide_amounts(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db)
        await execution_service.update_execution(
            db, USER_ID, item.id, payload(), "snapshot-key", ("127.0.0.1", "pytest")
        )

        snapshots = list(
            (
                await db.execute(
                    select(PortfolioSnapshot)
                    .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                    .order_by(PortfolioSnapshot.created_at, PortfolioSnapshot.id)
                )
            ).scalars()
        )
        mutation = await db.scalar(select(ExecutionMutation))
        event = await db.scalar(select(PortfolioEvent))
        audit = await db.scalar(select(AuditLog))
        execution_snapshots = [
            snapshot for snapshot in snapshots if snapshot.reason.startswith("execution_")
        ]
        by_reason = {snapshot.reason: snapshot for snapshot in execution_snapshots}
        assert set(by_reason) == {"execution_before", "execution_after"}
        assert (by_reason["execution_before"].cash, by_reason["execution_after"].cash) == (
            Decimal("2000"),
            Decimal("995"),
        )
        assert by_reason["execution_after"].market_value == Decimal("1005")
        assert by_reason["execution_after"].price_date is None
        assert by_reason["execution_after"].positions[0]["valuation_warning"] == (
            "000001缺少最新行情，已按成本价估值"
        )
        assert mutation.portfolio_event_ids == [str(event.id)]
        assert mutation.before_state is None
        assert mutation.after_state["item"]["execution"]["price"] == "10.0000"
        assert audit.detail == {
            "symbols": ["000001"],
            "symbol_count": 1,
            "portfolio_event_count": 1,
        }
        assert not ({"cash", "price", "fee", "quantity"} & set(audit.detail))


@pytest.mark.asyncio
async def test_execution_snapshot_uses_latest_market_value_instead_of_book_cost(
    session_factory,
):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(
            db,
            action="increase",
            cash=Decimal("3000"),
            position_quantity=100,
            position_total_cost=Decimal("800"),
        )
        db.add_all(
            [
                DailyBar(
                    id=1,
                    symbol=item.symbol,
                    trade_date=SIGNAL_DATE,
                    open=Decimal("12"),
                    high=Decimal("12"),
                    low=Decimal("12"),
                    close=Decimal("12"),
                    volume=Decimal("1"),
                ),
                DailyBar(
                    id=2,
                    symbol=item.symbol,
                    trade_date=SIGNAL_DATE + timedelta(days=10),
                    open=Decimal("99"),
                    high=Decimal("99"),
                    low=Decimal("99"),
                    close=Decimal("99"),
                    volume=Decimal("1"),
                ),
            ]
        )
        await db.flush()

        await execution_service.update_execution(
            db,
            USER_ID,
            item.id,
            payload(fee=Decimal("0"), acknowledge=True),
            "market-snapshot",
            None,
        )

        snapshots = list(
            (
                await db.execute(
                    select(PortfolioSnapshot).where(
                        PortfolioSnapshot.portfolio_id == portfolio.id,
                        PortfolioSnapshot.reason.in_(("execution_before", "execution_after")),
                    )
                )
            ).scalars()
        )
        by_reason = {snapshot.reason: snapshot for snapshot in snapshots}
        before = by_reason["execution_before"]
        after = by_reason["execution_after"]
        assert before.market_value == Decimal("1200")
        assert before.total_asset == Decimal("4200")
        assert before.price_date == SIGNAL_DATE
        assert before.positions[0]["latest_close"] == "12.0000"
        assert before.positions[0]["valuation_warning"] is None
        assert after.market_value == Decimal("2400")
        assert after.total_asset == Decimal("4400")
        assert after.price_date == SIGNAL_DATE
        assert after.positions[0]["latest_close"] == "12.0000"
        assert after.positions[0]["valuation_warning"] is None


@pytest.mark.asyncio
async def test_owner_isolation_returns_404_and_uses_no_foreign_portfolio(session_factory):
    async with session_factory() as db:
        portfolio, _advice, item = await seed_advice(db, user_id=OTHER_USER_ID)
        initial_snapshots = await count_rows(db, PortfolioSnapshot)

        with pytest.raises(HTTPException) as exc:
            await execution_service.update_execution(
                db, USER_ID, item.id, payload(), "owner-key", None
            )

        assert exc.value.status_code == 404
        assert portfolio.cash == Decimal("2000")
        assert await count_rows(db, ExecutionRecord) == 0
        assert await count_rows(db, ExecutionMutation) == 0
        assert await count_rows(db, PortfolioEvent) == 0
        assert await count_rows(db, PortfolioSnapshot) == initial_snapshots
