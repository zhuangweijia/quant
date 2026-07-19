# Portfolio Daily Action Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first complete Quant Desk decision loop: investment-profile and portfolio initialization, daily personalized position advice, manual execution recording, and immediate portfolio updates.

**Architecture:** Add a versioned investment-profile aggregate, one materialized CNY portfolio per user, immutable daily-advice versions, and append-only execution audit events. Keep allocation math in a pure advice engine, persistence and ownership checks in focused services, and expose thin authenticated FastAPI routes consumed by two Pinia stores and three Vue page flows.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, SQLAlchemy asyncio, Alembic, PostgreSQL, pytest, Vue 3, TypeScript 6, Pinia, Vue Router, Reka UI components, Vitest.

## Global Constraints

- Each user has exactly one CNY A-share portfolio in phase one.
- The investable universe remains exactly `csi300` and long-only.
- Do not add brokerage connectivity, automatic orders, margin, shorting, derivatives, intraday advice, multiple portfolios, or review analytics.
- Advice is generated after the signal-date close and is intended for the next open trading session; the UI says “下一交易日” until that session is observed.
- A newer `DailyBar.trade_date` than the advice signal date expires unresolved advice.
- Every actionable item includes target weight, target quantity, reference price, price band, reason, risk, and invalidation conditions.
- User-entered maximum drawdown is a historical-scenario constraint, never a future-loss guarantee.
- Missing or stale holdings block exact quantities; do not silently substitute zero positions.
- Money uses `Decimal`/SQL `Numeric`; timestamps are stored timezone-aware in UTC and displayed in Asia/Shanghai.
- Formal advice content, source snapshots, profile versions, execution audit events, and superseded versions are immutable; only advice lifecycle status and supersession pointers may change.
- Manual execution may update holdings; no other advice operation may mutate holdings.
- Actual fees come from user execution input; allocation reserves a configurable estimated-cost buffer rather than claiming an official fee schedule.
- Ordinary-user navigation in phase one is `今日`, `持仓`, `选股`, `市场`; hide `复盘` until phase three exists.
- Administrator-only navigation contains the existing analysis-task and model pages; ordinary users render neither links nor controls.
- Existing `/dashboard` and `/ranking` URLs remain as redirects to `/today` and `/selection`.
- Every page distinguishes loading, empty, stale, background-running, validation-error, and request-error states.
- Follow red-green-refactor for every task and commit only after focused tests pass.

## File Structure

### Backend

- `backend/app/models/investment_profile.py` — immutable versioned risk profiles.
- `backend/app/models/portfolio.py` — portfolio, positions, ledger events, and snapshots.
- `backend/app/models/advice.py` — immutable advice headers and action items.
- `backend/app/models/execution.py` — current execution aggregate plus append-only mutations.
- `backend/alembic/versions/c2d4e6f8a0b1_add_portfolio_decision_domain.py` — phase-one schema.
- `backend/app/schemas/portfolio.py` — setup, profile, holdings, cash, and portfolio DTOs.
- `backend/app/schemas/advice.py` — advice and execution DTOs.
- `backend/app/services/portfolio_service.py` — setup, valuation, reconciliation, profile versions, cash events, and snapshots.
- `backend/app/services/advice_engine.py` — pure constrained-allocation engine.
- `backend/app/services/advice_service.py` — prediction loading, advice version persistence, expiry, and per-user generation.
- `backend/app/services/execution_service.py` — idempotent execution updates and atomic portfolio mutations.
- `backend/app/api/v1/portfolio.py` — authenticated portfolio endpoints.
- `backend/app/api/v1/advice.py` — authenticated today/generate/execute endpoints.
- `backend/app/services/analysis_pipeline.py` — run per-user advice generation after rankings.
- `backend/app/core/events.py` — advice-ready event topic.
- `backend/tests/test_portfolio_models.py` — mapping and migration contract.
- `backend/tests/test_portfolio_schemas.py` — ranges and cross-field validation.
- `backend/tests/test_portfolio_service.py` — setup, reconciliation, cash, ownership, and snapshots.
- `backend/tests/test_advice_engine.py` — allocation, drawdown, concentration, turnover, and lot sizing.
- `backend/tests/test_advice_service.py` — idempotent versions, expiry, invalid inputs, and isolation.
- `backend/tests/test_execution_service.py` — execution, correction, idempotency, cash, and quantities.
- `backend/tests/test_portfolio_advice_api.py` — response and authorization contracts.

### Frontend

- `frontend/src/types/portfolio.ts` — setup/profile/portfolio types.
- `frontend/src/types/advice.ts` — advice/action/execution types.
- `frontend/src/api/portfolio.ts` and `.test.ts` — typed portfolio client.
- `frontend/src/api/advice.ts` and `.test.ts` — typed advice client.
- `frontend/src/stores/portfolio.ts` and `.test.ts` — setup and portfolio state.
- `frontend/src/stores/advice.ts` and `.test.ts` — today and execution state.
- `frontend/src/navigation/items.ts` and `.test.ts` — one role-aware navigation source.
- `frontend/src/components/app-sidebar/index.vue` — Quant Desk branding and grouped links.
- `frontend/src/components/command-menu/index.vue` — reuse role-aware links.
- `frontend/src/components/layout/AppLayout.vue` — mount the command menu and keep the page shell.
- `frontend/src/router/routes.ts`, `guards.ts`, and `types/vue-router.d.ts` — new routes and admin guard.
- `frontend/src/views/admin/AnalysisTasksView.vue` — existing setup/pipeline operations without user recommendations.
- `frontend/src/views/portfolio-setup/PortfolioSetupView.vue` and `.test.ts` — resumable four-step onboarding.
- `frontend/src/components/portfolio/HoldingsEditor.vue` and `.test.ts` — reusable cash/position editor.
- `frontend/src/views/portfolio/PortfolioView.vue` and `.test.ts` — portfolio summary, profile constraints, positions, reconciliation, and cash changes.
- `frontend/src/views/today/TodayView.vue` and `.test.ts` — today-state orchestration.
- `frontend/src/views/today/TodaySummaryCard.vue` — portfolio/advice metadata.
- `frontend/src/views/today/AdviceActionList.vue` and `.test.ts` — prioritized actions and collapsed holds.
- `frontend/src/views/today/ExecutionDialog.vue` and `.test.ts` — execution, partial, skipped, expired, and correction input.

---

### Task 1: Add the Portfolio Decision Database Domain

**Files:**
- Create: `backend/app/models/investment_profile.py`
- Create: `backend/app/models/portfolio.py`
- Create: `backend/app/models/advice.py`
- Create: `backend/app/models/execution.py`
- Create: `backend/alembic/versions/c2d4e6f8a0b1_add_portfolio_decision_domain.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_portfolio_models.py`

**Interfaces:**
- Produces: `InvestmentProfile`, `Portfolio`, `Position`, `PortfolioEvent`, `PortfolioSnapshot`, `DailyAdvice`, `AdviceItem`, `ExecutionRecord`, and `ExecutionMutation`.
- Produces database constraints `uq_investment_profile_user_version`, `uq_portfolio_user`, `uq_position_portfolio_symbol`, `uq_advice_user_signal_version`, `uq_advice_item_symbol`, `uq_execution_item`, and `uq_execution_mutation_key`.
- Consumes: `User.id`, `Stock.symbol`, `ModelVersion.version`, `Base`, `UUIDMixin`, `TimestampMixin`, and `JsonType`.

- [ ] **Step 1: Write failing model-contract tests**

```python
# backend/tests/test_portfolio_models.py
from app.models.advice import AdviceItem, DailyAdvice
from app.models.execution import ExecutionMutation, ExecutionRecord
from app.models.investment_profile import InvestmentProfile
from app.models.portfolio import Portfolio, PortfolioEvent, PortfolioSnapshot, Position


def test_phase_one_tables_and_unique_contracts():
    assert InvestmentProfile.__tablename__ == "investment_profiles"
    assert Portfolio.__tablename__ == "portfolios"
    assert Position.__tablename__ == "portfolio_positions"
    assert PortfolioEvent.__tablename__ == "portfolio_events"
    assert PortfolioSnapshot.__tablename__ == "portfolio_snapshots"
    assert DailyAdvice.__tablename__ == "daily_advices"
    assert AdviceItem.__tablename__ == "advice_items"
    assert ExecutionRecord.__tablename__ == "execution_records"
    assert ExecutionMutation.__tablename__ == "execution_mutations"
    assert Portfolio.__table__.c.currency.default.arg == "CNY"
    assert InvestmentProfile.__table__.c.is_active.default.arg is True
    assert DailyAdvice.__table__.c.status.default.arg == "ready"
    assert ExecutionRecord.__table__.c.revision.default.arg == 0


def test_money_and_weight_columns_keep_decimal_precision():
    assert str(Portfolio.__table__.c.cash.type) == "NUMERIC(20, 4)"
    assert str(Position.__table__.c.total_cost.type) == "NUMERIC(20, 4)"
    assert str(InvestmentProfile.__table__.c.max_drawdown.type) == "NUMERIC(8, 6)"
    assert str(AdviceItem.__table__.c.target_weight.type) == "NUMERIC(10, 8)"
```

- [ ] **Step 2: Run the model tests and verify collection fails**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_models.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.advice'`.

- [ ] **Step 3: Implement the exact mapped aggregates**

Use UUID primary keys, `ondelete="CASCADE"` for user-owned aggregates, `JsonType` for portable JSON, and these fields:

```python
# backend/app/models/investment_profile.py
import uuid
from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class InvestmentProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investment_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_investment_profile_user_version"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    investment_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_stock_weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_industry_weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    min_cash_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_daily_turnover: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
```

```python
# backend/app/models/portfolio.py
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, JsonType, TimestampMixin, UUIDMixin


class Portfolio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("user_id", name="uq_portfolio_user"),)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[str] = mapped_column(String(8), default="CNY", nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    last_confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


class PortfolioEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_events"
    __table_args__ = (
        Index("ix_portfolio_event_portfolio_time", "portfolio_id", "occurred_at"),
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cash_delta: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolio_events.id"), nullable=True
    )
    payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_snapshots"
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_asset: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    positions: Mapped[list] = mapped_column(JsonType, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

```python
# backend/app/models/advice.py
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, JsonType, TimestampMixin, UUIDMixin


class DailyAdvice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "daily_advices"
    __table_args__ = (
        UniqueConstraint("user_id", "signal_date", "version", name="uq_advice_user_signal_version"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"))
    profile_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("investment_profiles.id"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("portfolio_snapshots.id"))
    signal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="ready", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_exposure: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    target_exposure: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    estimated_cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("daily_advices.id"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)


class AdviceItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "advice_items"
    __table_args__ = (UniqueConstraint("advice_id", "symbol", name="uq_advice_item_symbol"),)
    advice_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("daily_advices.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_weight: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price_tolerance: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    positive_factors: Mapped[list] = mapped_column(JsonType, nullable=False)
    risks: Mapped[list] = mapped_column(JsonType, nullable=False)
    invalidation_conditions: Mapped[list] = mapped_column(JsonType, nullable=False)
    constraint_notes: Mapped[list] = mapped_column(JsonType, nullable=False)
```

```python
# backend/app/models/execution.py
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, JsonType, TimestampMixin, UUIDMixin


class ExecutionRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execution_records"
    __table_args__ = (UniqueConstraint("advice_item_id", name="uq_execution_item"),)
    advice_item_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("advice_items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    disposition: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    within_price_band: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ExecutionMutation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execution_mutations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_execution_mutation_key"),)
    execution_id: Mapped[uuid.UUID] = mapped_column(UuidType(as_uuid=True), ForeignKey("execution_records.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    after_state: Mapped[dict] = mapped_column(JsonType, nullable=False)
    portfolio_event_ids: Mapped[list] = mapped_column(JsonType, nullable=False)
```

- [ ] **Step 4: Register models and write the explicit Alembic migration**

Add all nine classes to `backend/app/models/__init__.py`. The migration revision is `c2d4e6f8a0b1`, its `down_revision` is `f4c9e8a7b6d5`, and `upgrade()` creates the nine tables in dependency order with every field and named constraint above. Add indexes on `(user_id, is_active)`, `(portfolio_id, occurred_at)`, `(user_id, signal_date, status)`, and `(advice_id, status)`. `downgrade()` drops them in reverse order. Use generic `sa.JSON()` in the migration so PostgreSQL and SQLite schema checks both compile.

- [ ] **Step 5: Add SQLite test support and run the focused checks**

Add `aiosqlite>=0.20` to `[project.optional-dependencies].dev`, then run:

`uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_models.py -q`

Expected: PASS.

Run: `uv run --project backend alembic -c backend/alembic.ini upgrade head`

Expected: migration applies with head `c2d4e6f8a0b1`.

- [ ] **Step 6: Commit the database domain**

```bash
git add backend/app/models backend/alembic/versions/c2d4e6f8a0b1_add_portfolio_decision_domain.py backend/pyproject.toml backend/tests/test_portfolio_models.py
git commit -m "feat: add portfolio decision domain"
```

### Task 2: Define Portfolio and Advice Contracts

**Files:**
- Create: `backend/app/schemas/portfolio.py`
- Create: `backend/app/schemas/advice.py`
- Test: `backend/tests/test_portfolio_schemas.py`

**Interfaces:**
- Produces: `RiskLevel`, `InvestmentProfileInput`, `PositionInput`, `PortfolioSetupRequest`, `PortfolioSetupStatus`, `HoldingsReconcileRequest`, `CashMovementRequest`, `PortfolioResponse`, `AdviceTodayResponse`, and `ExecutionUpdateRequest`.
- Risk defaults: conservative `(0.10, 0.05, 0.20, 0.20, 0.20)`, balanced `(0.15, 0.08, 0.25, 0.10, 0.30)`, aggressive `(0.25, 0.12, 0.35, 0.05, 0.50)` ordered as max drawdown, max stock, max industry, min cash, max turnover.

- [ ] **Step 1: Write failing schema tests**

```python
# backend/tests/test_portfolio_schemas.py
from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.schemas.advice import ExecutionUpdateRequest
from app.schemas.portfolio import InvestmentProfileInput, PortfolioSetupRequest, PositionInput


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
```

- [ ] **Step 2: Run and verify the missing-schema failure**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_schemas.py -q`

Expected: FAIL during collection for missing portfolio/advice schemas.

- [ ] **Step 3: Implement strict portfolio schemas**

Use `ConfigDict(extra="forbid")`. Apply these exact ranges: horizon `20..2520`, max drawdown `0.03..0.50`, max stock `0.01..0.20`, max industry `0.05..0.50`, min cash `0..0.50`, max turnover `0.05..1.00`. Require `max_stock_weight <= max_industry_weight`; positive capital; non-negative cash and integer quantities; positive average cost; and unique symbols. The service, not Pydantic, compares declared capital with cash plus latest market value because cost basis is not current value; reject differences above `max(100 CNY, total_capital × 0.01)` and return the server valuation in the 422 detail.

```python
class InvestmentProfileInput(StrictModel):
    investment_horizon_days: int = Field(ge=20, le=2520)
    risk_level: Literal["conservative", "balanced", "aggressive"]
    max_drawdown: Decimal = Field(ge=Decimal("0.03"), le=Decimal("0.50"))
    max_stock_weight: Decimal = Field(ge=Decimal("0.01"), le=Decimal("0.20"))
    max_industry_weight: Decimal = Field(ge=Decimal("0.05"), le=Decimal("0.50"))
    min_cash_ratio: Decimal = Field(ge=0, le=Decimal("0.50"))
    max_daily_turnover: Decimal = Field(ge=Decimal("0.05"), le=1)


class PositionInput(StrictModel):
    symbol: str = Field(pattern=r"^\d{6}$")
    quantity: int = Field(ge=0)
    average_cost: Decimal = Field(gt=0)


class PortfolioSetupRequest(StrictModel):
    profile: InvestmentProfileInput
    total_capital: Decimal = Field(gt=0)
    cash: Decimal = Field(ge=0)
    positions: list[PositionInput] = Field(default_factory=list, max_length=300)
```

Also define setup status, profile response/version, portfolio summary/position, holdings reconcile with `expected_updated_at`, and positive-amount `deposit|withdrawal|fee` cash movements. `CashMovementRequest` includes `kind`, `amount`, timezone-aware `occurred_at`, and `note` limited to 256 characters.

- [ ] **Step 4: Implement advice and execution schemas**

```python
class ExecutionUpdateRequest(StrictModel):
    disposition: Literal["executed", "partial", "skipped"]
    quantity: int = Field(default=0, ge=0)
    price: Decimal | None = Field(default=None, gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    executed_at: datetime | None = None
    reason: str = Field(default="", max_length=512)
    expected_revision: int = Field(ge=0)
    acknowledge_outside_advice: bool = False

    @model_validator(mode="after")
    def coherent_execution(self):
        traded = self.disposition in {"executed", "partial"}
        if traded and (self.quantity <= 0 or self.price is None or self.executed_at is None):
            raise ValueError("执行或部分执行必须填写数量、价格和时间")
        if self.executed_at is not None and self.executed_at.tzinfo is None:
            raise ValueError("成交时间必须包含时区")
        if not traded and (self.quantity or self.price is not None or self.executed_at is not None):
            raise ValueError("未执行不能填写成交数据")
        return self
```

Define `AdviceState = not_generated|generating|ready|partially_handled|handled|expired|failed`, `AdviceItemResponse`, `DailyAdviceResponse`, `AdviceTodayResponse`, and `ExecutionResponse`. Serialize decimals as JSON numbers consistently with existing Pydantic defaults.

- [ ] **Step 5: Run schemas and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_schemas.py -q`

Expected: PASS.

```bash
git add backend/app/schemas/portfolio.py backend/app/schemas/advice.py backend/tests/test_portfolio_schemas.py
git commit -m "feat: define portfolio advice contracts"
```

### Task 3: Implement Portfolio Initialization and Profile Versions

**Files:**
- Create: `backend/app/services/portfolio_service.py`
- Create: `backend/app/api/v1/portfolio.py`
- Modify: `backend/app/api/v1/__init__.py`
- Test: `backend/tests/test_portfolio_service.py`
- Test: `backend/tests/test_portfolio_advice_api.py`

**Interfaces:**
- Produces: `get_setup_status(db, user_id) -> PortfolioSetupStatus`, `complete_setup(db, user_id, payload, request_meta) -> PortfolioResponse`, `create_profile_version(db, user_id, payload, request_meta) -> InvestmentProfileResponse`, and `get_portfolio_response(db, user_id) -> PortfolioResponse`.
- Produces endpoints `GET /api/v1/portfolio/setup-status`, `POST /api/v1/portfolio/setup`, `GET /api/v1/portfolio`, and `PUT /api/v1/portfolio/profile`.

- [ ] **Step 1: Write failing setup-service tests**

```python
# backend/tests/test_portfolio_service.py
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services import portfolio_service


@pytest.mark.asyncio
async def test_complete_setup_is_atomic_and_creates_opening_snapshot(monkeypatch):
    repo = SimpleNamespace(
        get_portfolio=AsyncMock(return_value=None),
        create_profile=AsyncMock(return_value=SimpleNamespace(id="profile-1", version=1)),
        create_portfolio=AsyncMock(return_value=SimpleNamespace(id="portfolio-1")),
        replace_positions=AsyncMock(),
        create_snapshot=AsyncMock(),
        portfolio_response=AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    db = SimpleNamespace(flush=AsyncMock())
    payload = SimpleNamespace(profile=SimpleNamespace(), cash=Decimal("9000"), positions=[])

    await portfolio_service.complete_setup(db, "00000000-0000-0000-0000-000000000001", payload, None)

    repo.create_profile.assert_awaited_once()
    repo.create_portfolio.assert_awaited_once()
    repo.create_snapshot.assert_awaited_once()
```

The same test file must include independently named cases `test_second_setup_returns_409`, `test_profile_update_creates_version_two`, `test_setup_status_reports_missing_profile_and_portfolio`, and `test_setup_queries_are_user_scoped`; each uses `AsyncMock` and asserts the exact status/version/user id described by its name.

- [ ] **Step 2: Run and verify missing service failure**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_service.py -q`

Expected: FAIL because `portfolio_service` does not exist.

- [ ] **Step 3: Implement a focused `PortfolioRepository` and setup service**

Keep `PortfolioRepository` in `portfolio_service.py`; it wraps SQLAlchemy queries and exposes the exact methods mocked above. `complete_setup()` must:

```python
async def complete_setup(db, user_id, payload, request_meta):
    repo = PortfolioRepository(db)
    if await repo.get_portfolio(user_id):
        raise HTTPException(status_code=409, detail="投资组合已经初始化")
    await validate_symbols(db, [item.symbol for item in payload.positions])
    profile = await repo.create_profile(user_id, 1, payload.profile)
    portfolio = await repo.create_portfolio(user_id, payload.cash)
    await repo.replace_positions(portfolio.id, payload.positions)
    await repo.create_opening_events(portfolio.id, payload.cash, payload.positions)
    await repo.create_snapshot(portfolio.id, "setup", "profile", str(profile.id))
    await log_action(
        db, user_id=user_id, action="portfolio.setup", resource_type="portfolio",
        resource_id=str(portfolio.id), detail={"positions": len(payload.positions)}
    )
    await db.flush()
    return await repo.portfolio_response(user_id)
```

Validate every symbol exists in `stocks` and has `in_csi300=True`. The opening snapshot values positions at the most recent available close on or before today; when a held symbol has no bar, use its entered average cost and set `price_date=None` plus a `valuation_warning` in the response.

- [ ] **Step 4: Implement profile version replacement**

Lock the active row with `SELECT ... FOR UPDATE`, mark it inactive, insert `version + 1`, audit old/new constraints, and flush once. Never update an existing profile row in place.

- [ ] **Step 5: Implement thin authenticated routes and API tests**

```python
@router.get("/setup-status", response_model=ResponseBase[PortfolioSetupStatus])
async def setup_status(user: CurrentUser, db: DBSession):
    return ResponseBase(data=await portfolio_service.get_setup_status(db, user.id))


@router.post("/setup", response_model=ResponseBase[PortfolioResponse])
async def setup_portfolio(user: CurrentUser, db: DBSession, payload: PortfolioSetupRequest, request: Request):
    return ResponseBase(
        data=await portfolio_service.complete_setup(
            db, user.id, payload, extract_request_info(request)
        )
    )
```

The other routes follow the same dependency pattern. API tests call route functions with `SimpleNamespace` users and mocked service functions; assert the current user id is always passed and a payload cannot provide another user id.

- [ ] **Step 6: Run focused tests and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_service.py backend/tests/test_portfolio_advice_api.py -q`

Expected: PASS.

```bash
git add backend/app/services/portfolio_service.py backend/app/api/v1/portfolio.py backend/app/api/v1/__init__.py backend/tests/test_portfolio_service.py backend/tests/test_portfolio_advice_api.py
git commit -m "feat: initialize user portfolios"
```

### Task 4: Add Holdings Reconciliation and Cash Events

**Files:**
- Modify: `backend/app/services/portfolio_service.py`
- Modify: `backend/app/api/v1/portfolio.py`
- Modify: `backend/tests/test_portfolio_service.py`
- Modify: `backend/tests/test_portfolio_advice_api.py`

**Interfaces:**
- Produces: `reconcile_holdings(db, user_id, payload, request_meta) -> PortfolioResponse` and `record_cash_movement(db, user_id, payload, request_meta) -> PortfolioResponse`.
- Produces endpoints `PUT /api/v1/portfolio/holdings` and `POST /api/v1/portfolio/cash-movements`.

- [ ] **Step 1: Add failing atomic-update tests**

```python
@pytest.mark.asyncio
async def test_reconcile_rejects_stale_updated_at(monkeypatch):
    repo = SimpleNamespace(
        lock_portfolio=AsyncMock(return_value=SimpleNamespace(updated_at="newer")),
    )
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    with pytest.raises(HTTPException) as exc:
        await portfolio_service.reconcile_holdings(
            SimpleNamespace(), "user-1",
            SimpleNamespace(expected_updated_at="older", cash=Decimal("100"), positions=[]), None,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_withdrawal_cannot_make_cash_negative(monkeypatch):
    repo = SimpleNamespace(lock_portfolio=AsyncMock(return_value=SimpleNamespace(cash=Decimal("50"))))
    monkeypatch.setattr(portfolio_service, "PortfolioRepository", lambda db: repo)
    with pytest.raises(HTTPException) as exc:
        await portfolio_service.record_cash_movement(
            SimpleNamespace(), "user-1", SimpleNamespace(kind="withdrawal", amount=Decimal("100")), None
        )
    assert exc.value.status_code == 422
```

The same test file must include `test_reconcile_writes_before_and_after_snapshots`, `test_deposit_has_positive_cash_delta`, `test_withdrawal_has_negative_cash_delta`, and `test_fee_has_negative_cash_delta`. Assert `create_snapshot.await_args_list` reasons and exact signed `Decimal` deltas rather than only checking call counts.

- [ ] **Step 2: Run tests and verify failures**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_service.py -q`

Expected: FAIL for missing reconciliation and cash functions.

- [ ] **Step 3: Implement optimistic reconciliation**

Lock the portfolio row, compare `expected_updated_at`, validate symbols, capture a `before_reconcile` snapshot, replace materialized positions, set cash and `last_confirmed_at`, append one event whose payload contains complete before/after cash and positions, capture `after_reconcile`, audit counts only, and flush. Do not log the full private position payload.

- [ ] **Step 4: Implement signed cash events**

Map `deposit` to `+amount`, `withdrawal` and `fee` to `-amount`. Reject a negative resulting cash balance. Append the event before updating materialized cash, capture a snapshot after it, and return the recalculated portfolio response.

- [ ] **Step 5: Add routes, run tests, and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_service.py backend/tests/test_portfolio_advice_api.py -q`

Expected: PASS.

```bash
git add backend/app/services/portfolio_service.py backend/app/api/v1/portfolio.py backend/tests/test_portfolio_service.py backend/tests/test_portfolio_advice_api.py
git commit -m "feat: reconcile holdings and cash"
```

### Task 5: Build the Pure Constrained Advice Engine

**Files:**
- Create: `backend/app/services/advice_engine.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_advice_engine.py`

**Interfaces:**
- Produces immutable dataclasses `EngineProfile`, `EnginePosition`, `EngineCandidate`, `EngineLine`, and `EngineResult`.
- `EngineResult` includes deterministic `constraint_violations: tuple[str, ...]` so persistence and UI layers can surface constraints that cannot be reached in one trading day.
- Produces `build_advice(profile, cash, positions, candidates, estimated_cost_rate) -> EngineResult`.
- Consumes no database or network objects.

- [ ] **Step 1: Write failing allocation tests**

```python
# backend/tests/test_advice_engine.py
from decimal import Decimal
from app.services.advice_engine import (
    EngineCandidate, EnginePosition, EngineProfile, build_advice,
)


def candidate(symbol, industry, score, price="10", returns=None):
    return EngineCandidate(
        symbol=symbol, name=symbol, industry=industry, score=Decimal(score),
        rank=1, confidence="normal", price=Decimal(price),
        returns=tuple(returns or [0.001, -0.001] * 60),
        positive_factors=("评分靠前",), risks=("历史波动",),
    )


PROFILE = EngineProfile(
    max_drawdown=Decimal("0.15"), max_stock_weight=Decimal("0.10"),
    max_industry_weight=Decimal("0.20"), min_cash_ratio=Decimal("0.10"),
    max_daily_turnover=Decimal("0.30"), price_tolerance=Decimal("0.03"),
)


def test_engine_respects_stock_industry_cash_turnover_and_lots():
    result = build_advice(
        PROFILE, Decimal("100000"), (),
        (
            candidate("000001", "银行", "0.9"),
            candidate("000002", "银行", "0.8"),
            candidate("000003", "医药", "0.7"),
            candidate("000004", "消费", "0.6"),
        ), Decimal("0.001"),
    )
    assert all(line.target_weight <= PROFILE.max_stock_weight for line in result.lines)
    assert sum(line.target_weight for line in result.lines if line.industry == "银行") <= PROFILE.max_industry_weight
    assert result.estimated_cash >= result.total_asset * PROFILE.min_cash_ratio
    assert result.turnover <= PROFILE.max_daily_turnover
    assert all(line.target_quantity % 100 == 0 for line in result.lines if line.delta_quantity > 0)


def test_engine_scales_exposure_to_historical_drawdown_limit():
    stressed = candidate("000001", "银行", "0.9", returns=[-0.05] * 10 + [0.01] * 110)
    result = build_advice(PROFILE, Decimal("100000"), (), (stressed,), Decimal("0.001"))
    assert result.historical_max_drawdown <= PROFILE.max_drawdown


def test_engine_emits_exit_for_held_stock_outside_candidates():
    held = EnginePosition("600000", "浦发银行", "银行", 1000, Decimal("10"), Decimal("10000"))
    result = build_advice(PROFILE, Decimal("90000"), (held,), (), Decimal("0.001"))
    line = next(item for item in result.lines if item.symbol == "600000")
    assert line.action == "exit"
    assert line.target_quantity == 0
```

- [ ] **Step 2: Run and verify missing engine failure**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_advice_engine.py -q`

Expected: FAIL because `advice_engine` does not exist.

- [ ] **Step 3: Implement the deterministic engine**

Implement these exact stages in pure functions:

1. Reject non-positive cash, duplicate symbols, non-positive prices, fewer than 60 returns for a new candidate, held positions missing a price, `market_value != quantity × position.price`, or a held candidate whose price differs from the position reference price.
2. Compute total asset from cash plus current market values.
3. Score candidates by `score / max(population_stddev(returns), 0.005)`.
4. Allocate risky exposure `1 - min_cash_ratio` proportionally, iteratively capping stock and industry weights and returning unused weight to cash.
5. Form a 120-session portfolio-return series using the common tail; compute peak-to-trough drawdown. Binary-search a global risky-exposure multiplier in `[0, 1]` for 30 iterations until drawdown is within `max_drawdown`.
6. Compute one-way turnover as `sum(abs(target_weight-current_weight)) / 2`; blend current and proposed weights by `max_daily_turnover / turnover` when necessary.
7. Convert target value to quantities. New/increased positions round down to 100-share lots. A full exit may sell the complete held quantity; reductions round the reduction down to a 100-share multiple.
8. Reserve `estimated_cost_rate × traded_value`, reducing buy quantities until estimated cash is non-negative and at least the minimum cash amount.
9. Emit actions `exit`, `reduce`, `buy`, `increase`, or `hold`; sort in that order. After executable quantities are final, report remaining constraints as `cash_below_minimum`, `stock_cap_exceeded:<symbol>`, and `industry_cap_exceeded:<industry>` in category order and lexical suffix order. Use `industry_cap_exceeded:unknown` for the shared `None`-industry bucket.

The user-approved infeasible-portfolio policy is progressive correction: daily turnover and A-share lot rules remain hard execution limits. Keep the best executable final quantities even when an existing portfolio cannot reach stock, industry, or minimum-cash constraints today. Add clear Chinese notes to every affected engine line, do not claim all constraints were applied when violations remain, and return an empty violation tuple for feasible results. Task 6 must preserve and expose these machine-readable violations, and the advice UI must visibly surface them rather than presenting progressively constrained advice as fully compliant.

```python
def historical_max_drawdown(returns: tuple[float, ...]) -> Decimal:
    value = peak = 1.0
    worst = 0.0
    for daily_return in returns:
        value *= 1.0 + daily_return
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return Decimal(str(worst))
```

Add `TRANSACTION_COST_BUFFER_RATE: float = 0.001` and `ADVICE_PRICE_TOLERANCE: float = 0.03` to `Settings`; pass them into the engine rather than importing settings inside it.

- [ ] **Step 4: Run engine tests and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_advice_engine.py -q`

Expected: PASS.

```bash
git add backend/app/config.py backend/app/services/advice_engine.py backend/tests/test_advice_engine.py
git commit -m "feat: allocate constrained portfolio advice"
```

### Task 6: Persist and Generate Daily Advice

**Files:**
- Create: `backend/app/services/advice_service.py`
- Create: `backend/app/api/v1/advice.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/services/analysis_pipeline.py`
- Modify: `backend/app/core/events.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_advice_service.py`
- Modify: `backend/tests/test_portfolio_advice_api.py`
- Modify: `backend/tests/test_settings_api.py`

**Interfaces:**
- Produces: `generate_for_user(db, user_id, signal_date, force=False) -> DailyAdvice`, `generate_for_all_users(signal_date) -> dict`, `get_today_state(db, user_id) -> AdviceTodayResponse`, and `expire_stale_advice(db, user_id) -> None`.
- Produces `GET /api/v1/advice/today` and `POST /api/v1/advice/generate`.
- Produces event topic `advice:ready` with `user_id`, `advice_id`, and `signal_date`.

- [ ] **Step 1: Write failing service tests**

```python
# backend/tests/test_advice_service.py
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.services import advice_service


@pytest.mark.asyncio
async def test_generation_is_idempotent_without_force(monkeypatch):
    existing = SimpleNamespace(id="advice-1", status="ready")
    repo = SimpleNamespace(find_current=AsyncMock(return_value=existing))
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    result = await advice_service.generate_for_user(SimpleNamespace(), "user-1", date(2026, 7, 17))
    assert result is existing


@pytest.mark.asyncio
async def test_generation_rejects_incomplete_portfolio(monkeypatch):
    repo = SimpleNamespace(find_current=AsyncMock(return_value=None), load_inputs=AsyncMock(return_value=None))
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    with pytest.raises(HTTPException) as exc:
        await advice_service.generate_for_user(SimpleNamespace(), "user-1", date(2026, 7, 17))
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_newer_market_session_expires_unresolved_advice(monkeypatch):
    advice = SimpleNamespace(signal_date=date(2026, 7, 17), status="ready")
    repo = SimpleNamespace(latest_market_date=AsyncMock(return_value=date(2026, 7, 18)), expire=AsyncMock())
    monkeypatch.setattr(advice_service, "AdviceRepository", lambda db: repo)
    await advice_service.expire_if_needed(SimpleNamespace(), advice)
    repo.expire.assert_awaited_once_with(advice)
```

The same test file must include `test_force_generation_creates_next_version`, `test_failed_replacement_keeps_prior_current`, `test_batch_continues_after_one_user_failure`, and `test_missing_held_symbol_data_persists_failed_without_items`. Assert the exact version, supersession call order, per-user summary, and zero item count.

- [ ] **Step 2: Run and verify the missing service failure**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_advice_service.py -q`

Expected: FAIL because `advice_service` does not exist.

- [ ] **Step 3: Implement repository input loading and immutable persistence**

`AdviceRepository.load_inputs()` must load one active profile, the user's portfolio and positions, latest `Prediction` rows for the signal date, matching `Stock` metadata, same-date closes, and up to 120 daily returns. It must reject mixed model versions. Treat holdings as stale when an older advice has unresolved `pending` items after a newer market session exists; persist `failed/holdings_stale` rather than exact quantities. Create a source snapshot before calling `build_advice()`; persist the header and all items in one transaction. Map prediction explanation `positive` and `negative` arrays to factors/risks and add standard invalidation conditions for price-band breach, data invalidation, and session expiry.

`force=True` locks existing versions, writes the new version, flushes it, then marks the prior current advice `superseded` and links `superseded_by_id`. A failed replacement does not alter the prior version.

- [ ] **Step 4: Implement latest state and generation endpoints**

`GET /today` returns HTTP 200 for every state: `not_generated`, `generating`, `ready`, `partially_handled`, `handled`, `expired`, or `failed`. It calls expiry first. `POST /generate` selects the latest date that has ranked predictions and returns HTTP 409 when setup or predictions are missing; ordinary authenticated users may generate only their own advice.

- [ ] **Step 5: Add the pipeline stage and targeted event**

Append `portfolio_advice` after `ranking` in `STAGES`. Derive the signal date with `datetime.now(ZoneInfo("Asia/Shanghai")).date()` and pass it to `generate_for_all_users`. Per-user failures are returned in the summary and logged but do not fail rankings or other users. Publish `advice:ready` to each successful user's WebSocket; add the event topic to `main.py` forwarding subscriptions.

Update the existing pipeline-stage tests to expect the new stage and stub its generator.

- [ ] **Step 6: Run focused tests and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_advice_service.py backend/tests/test_portfolio_advice_api.py backend/tests/test_settings_api.py -q`

Expected: PASS.

```bash
git add backend/app/services/advice_service.py backend/app/api/v1/advice.py backend/app/api/v1/__init__.py backend/app/services/analysis_pipeline.py backend/app/core/events.py backend/app/main.py backend/tests/test_advice_service.py backend/tests/test_portfolio_advice_api.py backend/tests/test_settings_api.py
git commit -m "feat: generate daily user advice"
```

### Task 7: Record and Correct Manual Execution

**Files:**
- Create: `backend/app/services/execution_service.py`
- Modify: `backend/app/api/v1/advice.py`
- Test: `backend/tests/test_execution_service.py`
- Modify: `backend/tests/test_portfolio_advice_api.py`

**Interfaces:**
- Produces `update_execution(db, user_id, item_id, payload, idempotency_key, request_meta) -> ExecutionResponse`.
- Produces `PUT /api/v1/advice/items/{item_id}/execution`; requires `Idempotency-Key` header.

- [ ] **Step 1: Write failing execution tests**

```python
# backend/tests/test_execution_service.py
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.services import execution_service


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_existing_result(monkeypatch):
    mutation = SimpleNamespace(after_state={"revision": 1})
    repo = SimpleNamespace(find_mutation=AsyncMock(return_value=mutation), response_from_state=AsyncMock(return_value="same"))
    monkeypatch.setattr(execution_service, "ExecutionRepository", lambda db: repo)
    result = await execution_service.update_execution(SimpleNamespace(), "user-1", "item-1", SimpleNamespace(), "key-1", None)
    assert result == "same"


@pytest.mark.asyncio
async def test_buy_cannot_overdraw_cash(monkeypatch):
    locked = SimpleNamespace(action="buy", portfolio=SimpleNamespace(cash=Decimal("100")), record=None)
    repo = SimpleNamespace(find_mutation=AsyncMock(return_value=None), lock_owned_item=AsyncMock(return_value=locked))
    monkeypatch.setattr(execution_service, "ExecutionRepository", lambda db: repo)
    payload = SimpleNamespace(disposition="executed", quantity=100, price=Decimal("10"), fee=Decimal("5"), expected_revision=0, acknowledge_outside_advice=False)
    with pytest.raises(HTTPException) as exc:
        await execution_service.update_execution(SimpleNamespace(), "user-1", "item-1", payload, "key-2", None)
    assert exc.value.status_code == 422
```

The same file must contain named cases for sell quantity, partial status, price-band acknowledgement, expired acknowledgement, stale revision 409, correction reversal, later-symbol-event correction 409, advice aggregate status, before/after snapshots, and owner isolation. Each case asserts both the materialized portfolio delta and the corresponding append-only mutation/event calls.

- [ ] **Step 2: Run and verify missing service failure**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_execution_service.py -q`

Expected: FAIL because `execution_service` does not exist.

- [ ] **Step 3: Implement the locked idempotent mutation**

The service must execute in this order:

1. Return the prior mutation for an existing idempotency key.
2. Lock advice item, advice, portfolio, position, and current execution; include `DailyAdvice.user_id == user_id` in the ownership query.
3. Compare `expected_revision`; reject stale updates with 409.
4. Determine session expiry and price-band status. When outside advice and acknowledgement is false, return 409 without mutation.
5. Reject a correction if a later `PortfolioEvent` exists for the same symbol; instruct the user to reconcile holdings instead.
6. Capture a before snapshot.
7. Reverse the previous execution event when correcting, then apply the new cash/quantity/cost delta.
8. Recalculate average cost from `total_cost / quantity`; delete zero positions.
9. Upsert `ExecutionRecord`, increment revision, append `ExecutionMutation`, portfolio events, and an after snapshot.
10. Set item status and aggregate advice status, audit only symbols/counts, then flush.

Skipped records have no portfolio delta. Outside-band or expired acknowledged executions update the portfolio but persist `within_price_band=False` so later review can classify them.

- [ ] **Step 4: Add the route and API contract tests**

Read `Idempotency-Key` using `Header(min_length=8, max_length=64)`. Pass user id, item id, request metadata, and payload to the service. Never accept user or portfolio ids in the body.

- [ ] **Step 5: Run focused tests and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_execution_service.py backend/tests/test_portfolio_advice_api.py -q`

Expected: PASS.

```bash
git add backend/app/services/execution_service.py backend/app/api/v1/advice.py backend/tests/test_execution_service.py backend/tests/test_portfolio_advice_api.py
git commit -m "feat: record manual advice execution"
```

### Task 8: Add Typed Frontend APIs and Stores

**Files:**
- Create: `frontend/src/types/portfolio.ts`
- Create: `frontend/src/types/advice.ts`
- Create: `frontend/src/api/portfolio.ts`
- Create: `frontend/src/api/portfolio.test.ts`
- Create: `frontend/src/api/advice.ts`
- Create: `frontend/src/api/advice.test.ts`
- Create: `frontend/src/stores/portfolio.ts`
- Create: `frontend/src/stores/portfolio.test.ts`
- Create: `frontend/src/stores/advice.ts`
- Create: `frontend/src/stores/advice.test.ts`

**Interfaces:**
- Produces `portfolioApi`, `adviceApi`, `usePortfolioStore`, and `useAdviceStore` matching Tasks 2–7 exactly.
- `usePortfolioStore`: `setupStatus`, `portfolio`, `loading`, `error`, `loadSetupStatus`, `completeSetup`, `loadPortfolio`, `updateProfile`, `reconcileHoldings`, `recordCashMovement`.
- `useAdviceStore`: `today`, `loading`, `error`, `loadToday`, `generate`, `updateExecution`.

- [ ] **Step 1: Write failing API and store tests**

```ts
// frontend/src/api/advice.test.ts
import { describe, expect, it, vi } from 'vitest'
import client from './client'
import { adviceApi } from './advice'

vi.mock('./client', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }))

it('sends execution idempotency and revision', async () => {
  vi.mocked(client.put).mockResolvedValue({ data: {} } as never)
  await adviceApi.updateExecution('item-1', { disposition: 'skipped', quantity: 0, fee: 0, reason: '', expected_revision: 0, acknowledge_outside_advice: false }, 'mutation-123')
  expect(client.put).toHaveBeenCalledWith(
    '/api/v1/advice/items/item-1/execution', expect.any(Object),
    { headers: { 'Idempotency-Key': 'mutation-123' } },
  )
})
```

Store tests mock clients and assert errors do not erase the last successful state, setup success refreshes both status and portfolio, and execution success replaces the matching advice item and refreshes portfolio.

- [ ] **Step 2: Run and verify missing modules**

Run: `npm --prefix frontend test -- --run src/api/portfolio.test.ts src/api/advice.test.ts src/stores/portfolio.test.ts src/stores/advice.test.ts`

Expected: FAIL for missing modules.

- [ ] **Step 3: Implement exact DTOs and APIs**

Use string ISO datetimes and numbers for JSON decimals. Model the discriminated states and action values as string unions. Follow `settingsApi`'s `ApiResult<T>` cast because the Axios interceptor returns the unwrapped `ResponseBase`.

- [ ] **Step 4: Implement the stores**

Keep request errors as `error: string`; do not translate failed requests to empty data. Generate idempotency keys with `crypto.randomUUID()` in the store, not the component. After successful execution, call `Promise.all([loadToday(), portfolioStore.loadPortfolio()])`.

- [ ] **Step 5: Run tests and commit**

Run: `npm --prefix frontend test -- --run src/api/portfolio.test.ts src/api/advice.test.ts src/stores/portfolio.test.ts src/stores/advice.test.ts`

Expected: PASS.

```bash
git add frontend/src/types/portfolio.ts frontend/src/types/advice.ts frontend/src/api/portfolio.ts frontend/src/api/portfolio.test.ts frontend/src/api/advice.ts frontend/src/api/advice.test.ts frontend/src/stores/portfolio.ts frontend/src/stores/portfolio.test.ts frontend/src/stores/advice.ts frontend/src/stores/advice.test.ts
git commit -m "feat: add portfolio advice frontend state"
```

### Task 9: Rebuild Navigation Around Today and Roles

**Files:**
- Create: `frontend/src/navigation/items.ts`
- Create: `frontend/src/navigation/items.test.ts`
- Create: `frontend/src/views/admin/AnalysisTasksView.vue`
- Modify: `frontend/src/views/login/LoginView.vue`
- Modify: `frontend/src/components/app-sidebar/index.vue`
- Modify: `frontend/src/components/command-menu/index.vue`
- Modify: `frontend/src/components/layout/AppLayout.vue`
- Test: `frontend/src/components/app-sidebar/index.test.ts`

**Interfaces:**
- Produces `getPrimaryNav(role)` and `getAdminNav(role)`.
- Produces the single role-aware menu source and an administrator task page; Task 12 connects routes after all destination pages exist.

- [ ] **Step 1: Write failing role/navigation tests**

```ts
// frontend/src/navigation/items.test.ts
import { describe, expect, it } from 'vitest'
import { getAdminNav, getPrimaryNav } from './items'

it('shows the phase-one user path without unfinished review', () => {
  expect(getPrimaryNav('trader').map(item => item.title)).toEqual(['今日', '持仓', '选股', '市场'])
  expect(getAdminNav('trader')).toEqual([])
})

it('adds admin operations in a separate group', () => {
  expect(getAdminNav('admin').map(item => item.title)).toEqual(['分析任务', '模型与回测'])
})
```

Add sidebar tests asserting `Quant Desk`, no `Stock Analysis`/`Workspace`, and no admin links for a trader.

- [ ] **Step 2: Run and verify missing navigation module**

Run: `npm --prefix frontend test -- --run src/navigation/items.test.ts src/components/app-sidebar/index.test.ts`

Expected: FAIL for missing `navigation/items.ts`.

- [ ] **Step 3: Implement one role-aware navigation source**

Use icons as component references and exact items: primary `今日 /today`, `持仓 /portfolio`, `选股 /selection`, `市场 /market`; admin `分析任务 /admin/tasks`, `模型与回测 /model`. Sidebar and command menu both import these functions. Keep settings only in the user dropdown.

- [ ] **Step 4: Prepare the administrator page and shared shell**

`AnalysisTasksView` extracts setup and Pipeline status from the old dashboard but removes Top 10 and recommendation cards. Mount `CommandMenu` once in `AppLayout`; no global stock search is added in phase one. Update login copy to “查看下一交易日组合建议、仓位调整依据与主要风险”。 Route changes wait until Task 12 so every lazy import resolves when introduced.

- [ ] **Step 5: Run navigation tests/build and commit**

Run: `npm --prefix frontend test -- --run src/navigation/items.test.ts src/components/app-sidebar/index.test.ts`

Expected: PASS.

Run: `npm --prefix frontend run build`

Expected: PASS.

```bash
git add frontend/src/navigation frontend/src/views/admin/AnalysisTasksView.vue frontend/src/views/login/LoginView.vue frontend/src/components/app-sidebar frontend/src/components/command-menu frontend/src/components/layout/AppLayout.vue
git commit -m "feat: align navigation with daily decisions"
```

### Task 10: Build Resumable Portfolio Setup

**Files:**
- Create: `frontend/src/components/portfolio/HoldingsEditor.vue`
- Create: `frontend/src/components/portfolio/HoldingsEditor.test.ts`
- Create: `frontend/src/views/portfolio-setup/PortfolioSetupView.vue`
- Create: `frontend/src/views/portfolio-setup/PortfolioSetupView.test.ts`

**Interfaces:**
- `HoldingsEditor` consumes `cash: number`, `positions: PositionInput[]`, `totalCapital?: number`; emits `update:cash` and `update:positions`.
- `PortfolioSetupView` consumes `usePortfolioStore.completeSetup(payload)` and routes to `/today` only after success.

- [ ] **Step 1: Write failing component tests**

```ts
// frontend/src/views/portfolio-setup/PortfolioSetupView.test.ts
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, expect, it, vi } from 'vitest'
import { usePortfolioStore } from '@/stores/portfolio'
import PortfolioSetupView from './PortfolioSetupView.vue'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

beforeEach(() => { setActivePinia(createPinia()); push.mockReset() })

it('cannot submit until every step is valid', async () => {
  const wrapper = mount(PortfolioSetupView, { global: { stubs: { HoldingsEditor: true } } })
  expect(wrapper.get('[data-testid="setup-submit"]').attributes('disabled')).toBeDefined()
})

it('submits one atomic setup payload and opens today', async () => {
  const store = usePortfolioStore()
  vi.spyOn(store, 'completeSetup').mockResolvedValue({} as never)
  const wrapper = mount(PortfolioSetupView)
  await wrapper.get('#risk-level').setValue('balanced')
  await wrapper.get('#horizon-days').setValue(120)
  await wrapper.get('#max-drawdown').setValue(15)
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
  await wrapper.get('#max-stock-weight').setValue(8)
  await wrapper.get('#max-industry-weight').setValue(25)
  await wrapper.get('#min-cash-ratio').setValue(10)
  await wrapper.get('#max-daily-turnover').setValue(30)
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
  await wrapper.get('#total-capital').setValue(100000)
  await wrapper.get('#portfolio-cash').setValue(100000)
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
  await wrapper.get('[data-testid="setup-submit"]').trigger('click')
  await flushPromises()
  expect(store.completeSetup).toHaveBeenCalledWith(expect.objectContaining({ cash: 100000, positions: [] }))
  expect(push).toHaveBeenCalledWith('/today')
})
```

The same test file must include `test_duplicate_symbols_block_next_step`, `test_server_valuation_error_keeps_form`, `test_back_preserves_entered_values`, and `test_saved_draft_restores_current_step`. Assert the visible inline message, unchanged input values, and exact draft key `quant-desk:portfolio-setup:v1`.

- [ ] **Step 2: Run and verify missing views**

Run: `npm --prefix frontend test -- --run src/components/portfolio/HoldingsEditor.test.ts src/views/portfolio-setup/PortfolioSetupView.test.ts`

Expected: FAIL for missing components.

- [ ] **Step 3: Implement `HoldingsEditor`**

Render cash plus repeatable rows with stable fields `holding-symbol-{index}`, `holding-quantity-{index}`, and `holding-cost-{index}`. Normalize symbols to six digits, reject duplicates, emit immutable arrays, and show calculated cost value. Do not fetch quotes or silently change entered values.

- [ ] **Step 4: Implement the four-step setup page**

Steps are `风险与期限`, `组合约束`, `资金与持仓`, and `确认`. Risk-level selection fills the exact Task 2 defaults but leaves fields editable. Use the exact ids in the test above. Persist a versioned draft under `quant-desk:portfolio-setup:v1`; never store passwords or tokens in it. On submit, perform only syntactic checks locally, call `completeSetup` so the server can compare capital with latest market valuation, remove the draft, then `router.push('/today')`. Display API valuation/error detail without clearing inputs.

- [ ] **Step 5: Run tests/build and commit**

Run: `npm --prefix frontend test -- --run src/components/portfolio/HoldingsEditor.test.ts src/views/portfolio-setup/PortfolioSetupView.test.ts`

Expected: PASS.

```bash
git add frontend/src/components/portfolio frontend/src/views/portfolio-setup
git commit -m "feat: guide portfolio initialization"
```

### Task 11: Build the Portfolio Workspace

**Files:**
- Create: `frontend/src/views/portfolio/PortfolioView.vue`
- Create: `frontend/src/views/portfolio/PortfolioView.test.ts`

**Interfaces:**
- Consumes `usePortfolioStore.loadPortfolio`, `updateProfile`, `reconcileHoldings`, `recordCashMovement`, and reusable `HoldingsEditor`.
- Produces stable actions `portfolio-profile-edit`, `portfolio-reconcile`, `portfolio-cash-movement`, and `portfolio-retry`.

- [ ] **Step 1: Write failing page-state tests**

```ts
// frontend/src/views/portfolio/PortfolioView.test.ts
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, expect, it, vi } from 'vitest'
import { usePortfolioStore } from '@/stores/portfolio'
import PortfolioView from './PortfolioView.vue'

beforeEach(() => setActivePinia(createPinia()))

it('shows request errors separately from an empty portfolio', async () => {
  const store = usePortfolioStore()
  vi.spyOn(store, 'loadPortfolio').mockRejectedValue(new Error('网络不可用'))
  const wrapper = mount(PortfolioView)
  await flushPromises()
  expect(wrapper.text()).toContain('网络不可用')
  expect(wrapper.text()).not.toContain('暂无持仓')
  expect(wrapper.find('[data-testid="portfolio-retry"]').exists()).toBe(true)
})
```

The same test file must include `test_renders_summary_totals`, `test_cash_only_portfolio_is_not_request_error`, `test_reconcile_sends_current_updated_at`, `test_cash_movement_requires_positive_amount`, `test_profile_edit_creates_new_version`, and `test_conflict_refreshes_without_dropping_edits`.

- [ ] **Step 2: Run and verify the missing page**

Run: `npm --prefix frontend test -- --run src/views/portfolio/PortfolioView.test.ts`

Expected: FAIL for missing page.

- [ ] **Step 3: Implement the portfolio page**

Use `BasicPage title="持仓"`. Summary cards show total asset, cash, market value, exposure, valuation date, and last confirmation. A profile card shows the active version and all constraints and opens an edit form that calls `updateProfile`. The table shows symbol/name/industry, quantity, average cost, latest close, market value, P&L, current weight, and target weight when an advice exists. Reconciliation opens a dialog with `HoldingsEditor`, editable current cash, and `expected_updated_at`; cash movement opens a separate dialog with `deposit|withdrawal|fee`, positive amount, occurred time, and note.

Show valuation warnings inline. A 409 keeps edits, refreshes the latest portfolio, and asks the user to review differences before resubmitting.

- [ ] **Step 4: Run tests and commit**

Run: `npm --prefix frontend test -- --run src/views/portfolio/PortfolioView.test.ts`

Expected: PASS.

```bash
git add frontend/src/views/portfolio/PortfolioView.vue frontend/src/views/portfolio/PortfolioView.test.ts
git commit -m "feat: add portfolio workspace"
```

### Task 12: Build Today Actions and Execution Recording

**Files:**
- Create: `frontend/src/views/today/TodaySummaryCard.vue`
- Create: `frontend/src/views/today/AdviceActionList.vue`
- Create: `frontend/src/views/today/AdviceActionList.test.ts`
- Create: `frontend/src/views/today/ExecutionDialog.vue`
- Create: `frontend/src/views/today/ExecutionDialog.test.ts`
- Create: `frontend/src/views/today/TodayView.vue`
- Create: `frontend/src/views/today/TodayView.test.ts`
- Modify: `frontend/src/router/routes.ts`
- Modify: `frontend/src/router/guards.ts`
- Modify: `frontend/src/types/vue-router.d.ts`

**Interfaces:**
- `AdviceActionList` consumes `AdviceItem[]` and emits `execute(item)`.
- `ExecutionDialog` consumes `item`, `existingExecution`, and `open`; emits `submit(ExecutionUpdate)`.
- `TodayView` consumes `usePortfolioStore.setupStatus` and `useAdviceStore.today`.
- Produces routes `/today`, `/portfolio/setup`, `/portfolio`, `/selection`, `/market`, `/admin/tasks`, `/model`, and `/settings`.

- [ ] **Step 1: Write failing action and execution tests**

```ts
// frontend/src/views/today/AdviceActionList.test.ts
import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import AdviceActionList from './AdviceActionList.vue'

it('orders exits before reductions and collapses holds', () => {
  const items = [
    { id: 'h', action: 'hold', symbol: '000003', status: 'pending' },
    { id: 'b', action: 'buy', symbol: '000002', status: 'pending' },
    { id: 'x', action: 'exit', symbol: '000001', status: 'pending' },
  ]
  const wrapper = mount(AdviceActionList, { props: { items } as never })
  expect(wrapper.findAll('[data-testid="advice-action"]').map(node => node.attributes('data-action'))).toEqual(['exit', 'buy'])
  expect(wrapper.text()).toContain('继续持有 1')
})
```

Execution tests assert skipped fields stay hidden, partial/executed require quantity/price/time, quantity is capped by delta/available position, revision is sent, and a 409 outside-band response reveals an explicit acknowledgement action.

Today tests cover `loading`, `setup_required`, `not_generated`, `generating`, `ready`, `partially_handled`, `handled`, `expired`, `failed`, and request-error states.

- [ ] **Step 2: Run and verify missing components**

Run: `npm --prefix frontend test -- --run src/views/today/AdviceActionList.test.ts src/views/today/ExecutionDialog.test.ts src/views/today/TodayView.test.ts`

Expected: FAIL for missing components.

- [ ] **Step 3: Implement summary and prioritized action list**

The summary displays total asset, current/target exposure, current/estimated cash, signal date, “下一交易日”, generated time, data date, model version, and stale warnings. Each action card shows current/target quantities and weights, reference price and ± tolerance, score/confidence, factors, risks, invalidation conditions, and constraint notes. Use exact order `exit, reduce, buy, increase, hold`; holds are collapsed by default.

- [ ] **Step 4: Implement execution dialog**

Support executed, partial, and skipped. Pre-fill expected quantity but never actual price. Require a reason for skipped actions. For corrections, include current revision and explain that later portfolio events require holdings reconciliation. On outside-band/expired 409, show the server reason and a separate `仍记录为实际成交` button that resubmits with `acknowledge_outside_advice=true`.

- [ ] **Step 5: Implement Today orchestration and connect routes**

Load setup status first. Incomplete setup uses `router.replace('/portfolio/setup')`. Complete setup loads today and portfolio concurrently. `not_generated` shows `生成首份建议`; `generating` shows progress without a fake empty list; `failed` displays the persisted error and retry; expired items remain read-only except acknowledged execution recording. Subscribe to `advice:ready` through `useWebSocket` and refresh only when the event belongs to the current user.

Then make `/` and `/dashboard` redirect to `/today`; `/ranking` redirect to `/selection`; `/selection` reuse `RankingView`; `/admin/tasks` use `AnalysisTasksView`; and `/model` set `meta.adminOnly=true`. Guard ordinary users with `NotFound`, and set the title with `document.title = String(to.meta.title || 'Quant Desk') + ' - Quant Desk'`.

- [ ] **Step 6: Run tests/build and commit**

Run: `npm --prefix frontend test -- --run src/views/today/AdviceActionList.test.ts src/views/today/ExecutionDialog.test.ts src/views/today/TodayView.test.ts`

Expected: PASS.

Run: `npm --prefix frontend run build`

Expected: PASS.

```bash
git add frontend/src/views/today frontend/src/router frontend/src/types/vue-router.d.ts
git commit -m "feat: deliver daily action workflow"
```

### Task 13: Verify the Complete Phase-One Loop

**Files:**
- Modify only files required by failures discovered in this task.
- Add regression tests beside the failing behavior; do not create a generic catch-all test file.

**Interfaces:**
- Consumes every phase-one interface.
- Produces a verified migration, API loop, responsive UI, and clean repository state.

- [ ] **Step 1: Run backend quality gates**

Run: `uv run --project backend --extra dev ruff check backend/app backend/tests`

Expected: PASS.

Run: `uv run --project backend --extra dev python -m pytest backend/tests -q`

Expected: PASS with no skipped phase-one tests.

- [ ] **Step 2: Verify migration upgrade and downgrade on a disposable database**

With the local Compose PostgreSQL service running and the default local development credentials, create and verify the explicitly named disposable database, point `DATABASE_URL` only for these commands, then run:

```powershell
docker compose exec -T postgres createdb -U quant quant_phase1_verify
docker compose exec -T postgres psql -U quant -d quant_phase1_verify -tAc "SELECT current_database()"
$env:DATABASE_URL = 'postgresql+asyncpg://quant:quant@127.0.0.1:5432/quant_phase1_verify'
uv run --project backend alembic -c backend/alembic.ini upgrade head
uv run --project backend alembic -c backend/alembic.ini downgrade f4c9e8a7b6d5
uv run --project backend alembic -c backend/alembic.ini upgrade head
Remove-Item Env:DATABASE_URL
```

Expected: the database check prints exactly `quant_phase1_verify`; all migration commands exit 0 and the final head is `c2d4e6f8a0b1`. Re-run the database-name check immediately before cleanup, then remove only this database:

```powershell
docker compose exec -T postgres psql -U quant -d quant_phase1_verify -tAc "SELECT current_database()"
docker compose exec -T postgres dropdb -U quant quant_phase1_verify
```

- [ ] **Step 3: Run frontend quality gates**

Run: `npm --prefix frontend test -- --run`

Expected: PASS.

Run: `npm --prefix frontend run build`

Expected: PASS with no TypeScript errors.

- [ ] **Step 4: Run an authenticated API smoke**

Using a disposable user, verify in order:

1. `GET /portfolio/setup-status` returns `complete=false`.
2. `POST /portfolio/setup` creates one profile and portfolio.
3. `POST /advice/generate` returns ready advice when ranked predictions exist, or the documented 409 when they do not.
4. `GET /advice/today` returns the same immutable version.
5. `PUT /advice/items/{id}/execution` with one idempotency key updates cash/position once.
6. Repeating the same request/key returns the same revision without a second mutation.
7. `GET /portfolio` reflects the actual execution.

Do not use or modify the user's real portfolio data.

- [ ] **Step 5: Perform browser acceptance checks**

At desktop and narrow viewport widths, verify:

- Login redirects an uninitialized user to setup.
- Setup draft survives refresh and successful setup opens Today.
- User navigation contains only Today, Portfolio, Selection, and Market.
- Admin navigation is separately grouped and ordinary users cannot open admin routes.
- Every Today state is visually distinct.
- Execution, correction, stale revision, and outside-band acknowledgement work.
- Portfolio reconciliation and cash changes retain edits on failure.
- Branding says Quant Desk everywhere.

- [ ] **Step 6: Commit verification fixes**

If verification changed code, run `git diff --name-only`, stage each printed path explicitly after confirming it belongs to the verification fix, rerun the affected focused tests, and commit with `git commit -m "test: verify portfolio decision loop"`.

If no files changed, do not create an empty commit.

## Phase-One Completion Criteria

- A new authenticated user can complete profile and portfolio setup without leaving the guided flow.
- A complete user lands on Today and sees a precise non-empty state even when no advice exists.
- Advice generation is user-isolated, idempotent, versioned, source-snapshotted, and constrained.
- Infeasible existing portfolios are corrected progressively without breaching daily turnover or A-share lot rules; remaining cash, stock, and industry violations are persisted and surfaced by the advice API and UI in deterministic order.
- An actionable recommendation contains all quantities, weights, reference-price, explanation, risk, and validity data required by the design.
- Manual execution and corrections are idempotent, audited, ownership-checked, and atomic with portfolio updates.
- Stale holdings, expired sessions, price-band breaches, and failed requests never masquerade as valid advice.
- Ordinary and administrator navigation is separated.
- Backend tests, frontend tests, production build, migration cycle, authenticated API smoke, and browser checks all pass.
