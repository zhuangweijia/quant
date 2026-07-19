from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseModel(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


JsonDecimal = Annotated[
    Decimal, PlainSerializer(float, return_type=float, when_used="json")
]


RiskLevel = Literal["conservative", "balanced", "aggressive"]

RISK_DEFAULTS: dict[RiskLevel, tuple[Decimal, Decimal, Decimal, Decimal, Decimal]] = {
    "conservative": (
        Decimal("0.10"), Decimal("0.05"), Decimal("0.20"), Decimal("0.20"), Decimal("0.20")
    ),
    "balanced": (
        Decimal("0.15"), Decimal("0.08"), Decimal("0.25"), Decimal("0.10"), Decimal("0.30")
    ),
    "aggressive": (
        Decimal("0.25"), Decimal("0.12"), Decimal("0.35"), Decimal("0.05"), Decimal("0.50")
    ),
}


class InvestmentProfileInput(StrictModel):
    investment_horizon_days: int = Field(ge=20, le=2520)
    risk_level: RiskLevel
    max_drawdown: JsonDecimal = Field(ge=Decimal("0.03"), le=Decimal("0.50"))
    max_stock_weight: JsonDecimal = Field(ge=Decimal("0.01"), le=Decimal("0.20"))
    max_industry_weight: JsonDecimal = Field(ge=Decimal("0.05"), le=Decimal("0.50"))
    min_cash_ratio: JsonDecimal = Field(ge=Decimal("0"), le=Decimal("0.50"))
    max_daily_turnover: JsonDecimal = Field(ge=Decimal("0.05"), le=Decimal("1.00"))

    @model_validator(mode="after")
    def coherent_constraints(self):
        if self.max_stock_weight > self.max_industry_weight:
            raise ValueError("单只股票权重不能超过行业权重")
        return self


class PositionInput(StrictModel):
    symbol: str = Field(pattern=r"^\d{6}$")
    quantity: int = Field(ge=0)
    average_cost: JsonDecimal = Field(gt=0)


class PortfolioSetupRequest(StrictModel):
    profile: InvestmentProfileInput
    total_capital: JsonDecimal = Field(gt=0)
    cash: JsonDecimal = Field(ge=0)
    positions: list[PositionInput] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def unique_symbols(self):
        symbols = [position.symbol for position in self.positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("持仓股票代码不能重复")
        return self


class PortfolioSetupStatus(ResponseModel):
    complete: bool
    has_profile: bool
    has_portfolio: bool
    missing: list[Literal["profile", "portfolio"]] = Field(default_factory=list)


class InvestmentProfileResponse(InvestmentProfileInput):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    version: int = Field(ge=1)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PortfolioPositionResponse(ResponseModel):
    id: UUID
    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    industry: str | None = None
    quantity: int = Field(ge=0)
    average_cost: JsonDecimal = Field(gt=0)
    latest_close: JsonDecimal
    price_date: date | None = None
    market_value: JsonDecimal = Field(ge=0)
    unrealized_pnl: JsonDecimal
    current_weight: JsonDecimal
    target_weight: JsonDecimal | None = None
    valuation_warning: str | None = None


class PortfolioSummaryResponse(ResponseModel):
    id: UUID
    currency: Literal["CNY"]
    cash: JsonDecimal = Field(ge=0)
    market_value: JsonDecimal = Field(ge=0)
    total_asset: JsonDecimal = Field(ge=0)
    exposure: JsonDecimal
    target_exposure: JsonDecimal | None = None
    valuation_date: date | None = None
    last_confirmed_at: datetime
    updated_at: datetime


class HoldingsReconcileRequest(StrictModel):
    expected_updated_at: datetime
    positions: list[PositionInput] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def coherent_reconcile(self):
        if self.expected_updated_at.tzinfo is None:
            raise ValueError("更新时间必须包含时区")
        symbols = [position.symbol for position in self.positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("持仓股票代码不能重复")
        return self


class CashMovementRequest(StrictModel):
    kind: Literal["deposit", "withdrawal", "fee"]
    amount: JsonDecimal = Field(gt=0)
    occurred_at: datetime
    note: str = Field(default="", max_length=256)

    @model_validator(mode="after")
    def aware_occurrence(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("发生时间必须包含时区")
        return self


class PortfolioResponse(ResponseModel):
    profile: InvestmentProfileResponse
    summary: PortfolioSummaryResponse
    positions: list[PortfolioPositionResponse]
    valuation_warnings: list[str] = Field(default_factory=list)
    updated_at: datetime
