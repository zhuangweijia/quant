"""Analysis pipeline API — trigger and status."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.models.analysis_run import AnalysisRun
from app.models.daily_bar import DailyBar
from app.models.model_version import ModelVersion
from app.models.stock import Stock
from app.schemas.common import ResponseBase
from app.schemas.model import AnalysisStatusResponse, AnalysisTriggerResponse

router = APIRouter()


@router.post("/trigger", response_model=ResponseBase[AnalysisTriggerResponse])
async def trigger_analysis(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可触发分析")

    stock_count = await db.scalar(
        select(func.count(Stock.id)).where(Stock.in_csi300.is_(True))
    ) or 0
    bar_count = await db.scalar(select(func.count(DailyBar.id))) or 0
    if stock_count <= 0 or bar_count <= 0:
        raise HTTPException(status_code=409, detail="请先完成市场数据初始化")

    active_result = await db.execute(
        select(ModelVersion.version)
        .where(ModelVersion.is_active.is_(True))
        .limit(1)
    )
    if active_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=409, detail="请先训练并激活模型")

    running_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.status == "running").limit(1)
    )
    running = running_result.scalar_one_or_none()
    if running:
        return ResponseBase(
            data=AnalysisTriggerResponse(run_id=running.run_id, status="running")
        )

    from app.services.analysis_pipeline import analysis_pipeline
    run_id = await analysis_pipeline.trigger("manual")
    return ResponseBase(data=AnalysisTriggerResponse(run_id=run_id))


@router.get("/status", response_model=ResponseBase[AnalysisStatusResponse])
async def get_analysis_status(db: DBSession):
    result = await db.execute(
        select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(1)
    )
    run = result.scalar_one_or_none()

    if not run:
        return ResponseBase(data=AnalysisStatusResponse(status="idle"))

    return ResponseBase(data=AnalysisStatusResponse(
        run_id=run.run_id,
        trigger_type=run.trigger_type,
        status=run.status,
        stages=run.stages,
        started_at=run.started_at.isoformat() if run.started_at else None,
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        error=run.error,
    ))
