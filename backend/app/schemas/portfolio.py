from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseModel(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


def require_decimal_string(value: object) -> Decimal | str:
    if isinstance(value, (Decimal, str)):
        return value
    raise ValueError("金额必须使用十进制字符串")


MonetaryDecimal = Annotated[
    Decimal,
    BeforeValidator(require_decimal_string),
    PlainSerializer(str, return_type=str, when_used="json"),
]
RatioDecimal = Annotated[
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
    max_drawdown: RatioDecimal = Field(ge=Decimal("0.03"), le=Decimal("0.50"))
    max_stock_weight: RatioDecimal = Field(ge=Decimal("0.01"), le=Decimal("0.20"))
    max_industry_weight: RatioDecimal = Field(ge=Decimal("0.05"), le=Decimal("0.50"))
    min_cash_ratio: RatioDecimal = Field(ge=Decimal("0"), le=Decimal("0.50"))
    max_daily_turnover: RatioDecimal = Field(ge=Decimal("0.05"), le=Decimal("1.00"))

    @model_validator(mode="after")
    def coherent_constraints(self):
        if self.max_stock_weight > self.max_industry_weight:
            raise ValueError("单只股票权重不能超过行业权重")
        return self


class PositionInput(StrictModel):
    symbol: str = Field(pattern=r"^\d{6}$")
    quantity: int = Field(ge=0)
    average_cost: MonetaryDecimal = Field(gt=0)


class PortfolioSetupRequest(StrictModel):
    profile: InvestmentProfileInput
    total_capital: MonetaryDecimal = Field(gt=0)
    cash: MonetaryDecimal = Field(ge=0)
    positions: list[PositionInput] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def unique_symbols(self):
        symbols = [position.symbol for position in self.positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("持仓股票代码不能重复")
        return self


class PortfolioSetupStatus(ResponseModel):
    complete: bool = False
    has_profile: bool
    has_portfolio: bool
    missing: list[Literal["profile", "portfolio"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def derived_status(self):
        complete = self.has_profile and self.has_portfolio
        missing = [
            name
            for name, present in (("profile", self.has_profile), ("portfolio", self.has_portfolio))
            if not present
        ]
        if "complete" in self.model_fields_set and self.complete != complete:
            raise ValueError("完成状态必须与配置状态一致")
        if "missing" in self.model_fields_set and self.missing != missing:
            raise ValueError("缺失项必须与配置状态一致")
        self.complete = complete
        self.missing = missing
        return self


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
    average_cost: MonetaryDecimal = Field(gt=0)
    latest_close: MonetaryDecimal
    price_date: date | None = None
    market_value: MonetaryDecimal = Field(ge=0)
    unrealized_pnl: MonetaryDecimal
    current_weight: RatioDecimal
    target_weight: RatioDecimal | None = None
    valuation_warning: str | None = None


class PortfolioSummaryResponse(ResponseModel):
    id: UUID
    currency: Literal["CNY"]
    cash: MonetaryDecimal = Field(ge=0)
    market_value: MonetaryDecimal = Field(ge=0)
    total_asset: MonetaryDecimal = Field(ge=0)
    exposure: RatioDecimal
    target_exposure: RatioDecimal | None = None
    valuation_date: date | None = None
    last_confirmed_at: datetime
    updated_at: datetime


class HoldingsReconcileRequest(StrictModel):
    expected_updated_at: datetime
    cash: MonetaryDecimal = Field(ge=0)
    positions: list[PositionInput] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def coherent_reconcile(self):
        require_aware_datetime(self.expected_updated_at, "更新时间必须包含时区")
        symbols = [position.symbol for position in self.positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("持仓股票代码不能重复")
        return self


class CashMovementRequest(StrictModel):
    kind: Literal["deposit", "withdrawal", "fee"]
    amount: MonetaryDecimal = Field(gt=0)
    occurred_at: datetime
    note: str = Field(default="", max_length=256)

    @model_validator(mode="after")
    def aware_occurrence(self):
        require_aware_datetime(self.occurred_at, "发生时间必须包含时区")
        return self


class PortfolioResponse(ResponseModel):
    profile: InvestmentProfileResponse
    summary: PortfolioSummaryResponse
    positions: list[PortfolioPositionResponse]
    valuation_warnings: list[str] = Field(default_factory=list)
    updated_at: datetime


def require_aware_datetime(value: datetime, message: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(message)
