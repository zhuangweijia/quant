from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.models.analysis_run import AnalysisRun
from app.models.daily_bar import DailyBar
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from app.models.setup_run import SetupRun
from app.models.stock import Stock
from app.schemas.common import ResponseBase
from app.schemas.setup import (
    SetupCounts,
    SetupRunItem,
    SetupStartResponse,
    SetupStatusResponse,
)
from app.services.setup_pipeline import setup_pipeline

router = APIRouter()


@router.get("/status", response_model=ResponseBase[SetupStatusResponse])
async def get_setup_status(user: CurrentUser, db: DBSession):
    stock_count = (
        await db.scalar(select(func.count(Stock.id)).where(Stock.in_csi300.is_(True))) or 0
    )
    bar_count = await db.scalar(select(func.count(DailyBar.id))) or 0
    model_count = await db.scalar(select(func.count(ModelVersion.id))) or 0
    prediction_count = (
        await db.scalar(
            select(func.count(Prediction.id)).where(Prediction.trade_date == date.today())
        )
        or 0
    )

    latest_result = await db.execute(select(SetupRun).order_by(SetupRun.started_at.desc()).limit(1))
    latest_run = latest_result.scalar_one_or_none()

    active_result = await db.execute(
        select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
    )
    active = active_result.scalar_one_or_none()
    active_version = getattr(active, "version", active)

    analysis_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.status == "running").limit(1)
    )
    running_analysis = analysis_result.scalar_one_or_none()

    if latest_run and latest_run.status == "running":
        readiness = "initializing"
    elif latest_run and latest_run.status in {"failed", "interrupted"}:
        readiness = "failed"
    elif (
        latest_run
        and latest_run.status == "completed"
        and active_version
        and stock_count
        and bar_count
    ):
        readiness = "ready"
    else:
        readiness = "uninitialized"

    run_item = None
    if latest_run:
        run_item = SetupRunItem(
            run_id=latest_run.run_id,
            status=latest_run.status,
            current_stage=latest_run.current_stage,
            stages=latest_run.stages or {},
            started_at=latest_run.started_at.isoformat(),
            finished_at=(latest_run.finished_at.isoformat() if latest_run.finished_at else None),
            error=latest_run.error,
        )

    is_admin = user.role == "admin"
    response = SetupStatusResponse(
        readiness=readiness,
        counts=SetupCounts(
            stocks=stock_count,
            daily_bars=bar_count,
            models=model_count,
            today_predictions=prediction_count,
        ),
        active_model=active_version,
        run=run_item,
        can_start=is_admin and readiness != "initializing",
        can_run_analysis=(is_admin and readiness == "ready" and running_analysis is None),
    )
    return ResponseBase(data=response)


@router.post(
    "/start",
    response_model=ResponseBase[SetupStartResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_setup(user: AdminUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可启动首次配置")

    run_id = await setup_pipeline.start()
    return ResponseBase(data=SetupStartResponse(run_id=run_id))
