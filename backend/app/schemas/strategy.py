from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: str | None = Field(None, max_length=1000)
    code: str = Field(..., min_length=1)
    params: dict | None = None
    market: str = Field(..., pattern=r"^(a_stock|us_stock|crypto)$")


class StrategyUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=128)
    description: str | None = None
    code: str | None = Field(None, min_length=1)
    params: dict | None = None


class StrategyListItem(BaseModel):
    id: UUID
    name: str
    market: str
    status: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyDetail(StrategyListItem):
    code: str
    params: dict | None

    model_config = {"from_attributes": True}
