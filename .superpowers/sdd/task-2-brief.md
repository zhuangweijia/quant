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

Define `AdviceState = not_generated|generating|ready|partially_handled|handled|expired|failed`, `AdviceItemResponse`, `DailyAdviceResponse`, `AdviceTodayResponse`, and `ExecutionResponse`. Serialize monetary values as decimal strings and bounded ratios, weights, tolerances, drawdown constraints, and scores as JSON numbers.

- [ ] **Step 5: Run schemas and commit**

Run: `uv run --project backend --extra dev python -m pytest backend/tests/test_portfolio_schemas.py -q`

Expected: PASS.

```bash
git add backend/app/schemas/portfolio.py backend/app/schemas/advice.py backend/tests/test_portfolio_schemas.py
git commit -m "feat: define portfolio advice contracts"
```
