"""Analysis pipeline API — trigger and status."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.model import AnalysisStatusResponse, AnalysisTriggerResponse
from app.models.analysis_run import AnalysisRun

router = APIRouter()


@router.post("/trigger", response_model=ResponseBase[AnalysisTriggerResponse])
async def trigger_analysis(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可触发分析")

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
