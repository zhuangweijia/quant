from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RiskRuleCreate(BaseModel):
    strategy_id: UUID | None = None
    rule_type: str = Field(
        ...,
        pattern=r"^(max_position_value|max_position_ratio|stop_loss|take_profit|daily_loss_limit|daily_trade_limit|blacklist|max_order_amount)$",
    )
    params: dict
    priority: int = 0


class RiskRuleUpdate(BaseModel):
    params: dict | None = None
    enabled: bool | None = None
    priority: int | None = None


class RiskRuleResponse(BaseModel):
    id: UUID
    strategy_id: UUID | None
    rule_type: str
    params: dict
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: UUID
    strategy_id: UUID | None
    level: str
    title: str
    message: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
