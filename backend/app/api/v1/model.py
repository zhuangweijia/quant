"""Model management API — version list, train trigger, activate."""

from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.model_version import ModelVersion
from app.schemas.common import ResponseBase
from app.schemas.model import (
    BacktestRequest,
    ModelVersionItem,
    ModelVersionListResponse,
    TrainResponse,
)

router = APIRouter()


@router.get("/versions", response_model=ResponseBase[ModelVersionListResponse])
async def list_versions(db: DBSession):
    result = await db.execute(select(ModelVersion).order_by(ModelVersion.trained_at.desc()))
    versions = [
        ModelVersionItem(
            version=v.version,
            trained_at=v.trained_at.isoformat() if v.trained_at else "",
            data_start=v.data_start,
            data_end=v.data_end,
            ic=v.ic,
            val_accuracy=v.val_accuracy,
            top_features=v.top_features,
            is_active=v.is_active,
            n_estimators=v.n_estimators,
        )
        for v in result.scalars().all()
    ]
    return ResponseBase(data=ModelVersionListResponse(versions=versions))


@router.post("/train", response_model=ResponseBase[TrainResponse])
async def trigger_training(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可触发训练")

    from app.services.ml_model import ml_model_service
    from app.services.settings_service import get_system_params

    try:
        runtime_params = await get_system_params(db)
        result = await ml_model_service.train(runtime_params)
        return ResponseBase(
            data=TrainResponse(
                version=result.get("version", ""),
                ic=result.get("ic"),
                val_accuracy=result.get("val_accuracy"),
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练失败: {e}")


@router.post("/{version}/activate", response_model=ResponseBase[dict])
async def activate_model(version: str, user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可激活模型")

    from app.services.ml_model import ml_model_service
    from app.services.settings_service import get_system_params

    try:
        runtime_params = await get_system_params(db)
        await ml_model_service.activate_model(db, version, runtime_params)
        return ResponseBase(data={"version": version, "activated": True})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/backtest", response_model=ResponseBase[dict])
async def run_backtest(payload: BacktestRequest, user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行回测")

    from app.services.model_validation_service import run_quintile_backtest

    result = await run_quintile_backtest(
        db=db,
        model_version=payload.model_version,
        start_date=payload.start_date or date.today().replace(year=date.today().year - 1),
        end_date=payload.end_date or date.today(),
    )
    return ResponseBase(data=result)
