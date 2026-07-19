from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.portfolio import (
    MonetaryDecimal,
    MonetaryInputDecimal,
    RatioDecimal,
    ResponseModel,
    StrictModel,
    require_aware_datetime,
)

AdviceState = Literal[
    "not_generated", "generating", "ready", "partially_handled", "handled", "expired", "failed"
]
AdviceAction = Literal["buy", "increase", "hold", "reduce", "exit"]
AdviceItemStatus = Literal["pending", "executed", "partial", "skipped", "expired"]


class ExecutionRecordResponse(ResponseModel):
    id: UUID
    disposition: Literal["executed", "partial", "skipped"]
    quantity: int
    price: MonetaryDecimal | None
    fee: MonetaryDecimal
    executed_at: datetime | None
    reason: str
    within_price_band: bool
    revision: int
    created_at: datetime
    updated_at: datetime


class AdviceItemResponse(ResponseModel):
    id: UUID
    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    industry: str | None = None
    action: AdviceAction
    status: AdviceItemStatus
    current_quantity: int = Field(ge=0)
    target_quantity: int = Field(ge=0)
    delta_quantity: int
    current_average_cost: MonetaryDecimal | None = None
    current_weight: RatioDecimal
    target_weight: RatioDecimal
    reference_price: MonetaryDecimal
    price_tolerance: RatioDecimal
    score: RatioDecimal
    rank: int | None = Field(default=None, ge=1)
    confidence: str
    positive_factors: list[str]
    risks: list[str]
    invalidation_conditions: list[str]
    constraint_notes: list[str]
    execution: ExecutionRecordResponse | None = None


class DailyAdviceResponse(ResponseModel):
    id: UUID
    signal_date: date
    version: int = Field(ge=1)
    status: AdviceState
    model_version: str
    data_date: date
    current_exposure: RatioDecimal = Field(ge=Decimal("0"), le=Decimal("1"))
    target_exposure: RatioDecimal = Field(ge=Decimal("0"), le=Decimal("1"))
    current_cash: MonetaryDecimal
    estimated_cash: MonetaryDecimal = Field(ge=0)
    total_asset: MonetaryDecimal
    generated_at: datetime
    portfolio_updated_at: datetime
    stale_warnings: list[str]
    constraint_violations: list[str] = Field(default_factory=list)
    items: list[AdviceItemResponse] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class AdviceTodayResponse(ResponseModel):
    state: AdviceState
    setup_required: bool = False
    advice: DailyAdviceResponse | None = None
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def coherent_today(self):
        requires_advice = {"ready", "partially_handled", "handled", "expired"}
        if self.state in requires_advice and self.advice is None:
            raise ValueError("可用建议状态必须包含建议内容")
        return self


class ExecutionUpdateRequest(StrictModel):
    disposition: Literal["executed", "partial", "skipped"]
    quantity: int = Field(default=0, ge=0)
    price: MonetaryInputDecimal | None = Field(default=None, gt=0)
    fee: MonetaryInputDecimal = Field(default=Decimal("0"), ge=0)
    executed_at: datetime | None = None
    reason: str = Field(default="", max_length=512)
    expected_revision: int = Field(ge=0)
    acknowledge_outside_advice: bool = False

    @model_validator(mode="after")
    def coherent_execution(self):
        traded = self.disposition in {"executed", "partial"}
        if traded and (self.quantity <= 0 or self.price is None or self.executed_at is None):
            raise ValueError("执行或部分执行必须填写数量、价格和时间")
        if self.executed_at is not None:
            require_aware_datetime(self.executed_at, "成交时间必须包含时区")
        if not traded and (
            self.quantity or self.price is not None or self.executed_at is not None or self.fee != 0
        ):
            raise ValueError("未执行不能填写成交数据")
        if not traded and not self.reason.strip():
            raise ValueError("未执行必须填写原因")
        return self


class ExecutionResponse(ResponseModel):
    item: AdviceItemResponse
    advice_state: AdviceState
