from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ModelVersionItem(BaseModel):
    version: str
    trained_at: str
    data_start: date
    data_end: date
    ic: Decimal | None = None
    val_accuracy: Decimal | None = None
    top_features: dict | None = None
    is_active: bool = False
    n_estimators: int = 200


class ModelVersionListResponse(BaseModel):
    versions: list[ModelVersionItem]


class TrainRequest(BaseModel):
    pass


class TrainResponse(BaseModel):
    version: str
    ic: Decimal | None = None
    val_accuracy: Decimal | None = None


class ActivateRequest(BaseModel):
    pass


class BacktestRequest(BaseModel):
    model_version: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class BacktestResponse(BaseModel):
    model_version: str
    start_date: date
    end_date: date
    group_returns: dict[str, list[dict]]
    ic_series: list[dict]
    metrics: dict


class AnalysisStatusResponse(BaseModel):
    run_id: str | None = None
    trigger_type: str | None = None
    status: str = "idle"
    stages: dict | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class AnalysisTriggerResponse(BaseModel):
    run_id: str
    status: str = "started"
