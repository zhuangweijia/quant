from typing import Literal

from pydantic import BaseModel, Field


SetupReadiness = Literal["uninitialized", "initializing", "failed", "ready"]
SetupRunStatus = Literal["running", "completed", "failed", "interrupted"]


class SetupCounts(BaseModel):
    stocks: int = 0
    daily_bars: int = 0
    models: int = 0
    today_predictions: int = 0


class SetupRunItem(BaseModel):
    run_id: str
    status: SetupRunStatus
    current_stage: str | None = None
    stages: dict = Field(default_factory=dict)
    started_at: str
    finished_at: str | None = None
    error: str | None = None


class SetupStatusResponse(BaseModel):
    readiness: SetupReadiness
    counts: SetupCounts
    active_model: str | None = None
    run: SetupRunItem | None = None
    can_start: bool = False
    can_run_analysis: bool = False


class SetupStartResponse(BaseModel):
    run_id: str
    status: str = "started"
