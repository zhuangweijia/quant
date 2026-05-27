from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, func, desc

from app.api.deps import CurrentUser, DBSession
from app.models.strategy import Strategy
from app.models.strategy_version import StrategyVersion
from app.schemas.common import ResponseBase, PageResponse
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class StrategyVersionResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    version: int
    code: str
    params: dict | None
    change_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{strategy_id}/versions", response_model=ResponseBase[list[StrategyVersionResponse]])
async def list_versions(
    strategy_id: UUID,
    user: CurrentUser,
    db: DBSession,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id:
        raise HTTPException(status_code=404, detail="策略不存在")

    result = await db.execute(
        select(StrategyVersion)
        .where(StrategyVersion.strategy_id == strategy_id)
        .order_by(desc(StrategyVersion.version))
        .limit(50)
    )
    versions = result.scalars().all()
    return ResponseBase(data=[StrategyVersionResponse.model_validate(v) for v in versions])


@router.get("/{strategy_id}/versions/{version_num}", response_model=ResponseBase[StrategyVersionResponse])
async def get_version(
    strategy_id: UUID,
    version_num: int,
    user: CurrentUser,
    db: DBSession,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id:
        raise HTTPException(status_code=404, detail="策略不存在")

    result = await db.execute(
        select(StrategyVersion).where(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.version == version_num,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    return ResponseBase(data=StrategyVersionResponse.model_validate(version))


class RollbackRequest(BaseModel):
    target_version: int


@router.post("/{strategy_id}/rollback", response_model=ResponseBase[StrategyVersionResponse])
async def rollback_version(
    strategy_id: UUID,
    user: CurrentUser,
    db: DBSession,
    payload: RollbackRequest,
):
    strategy = await db.get(Strategy, strategy_id)
    if not strategy or strategy.user_id != user.id:
        raise HTTPException(status_code=404, detail="策略不存在")
    if strategy.status == "running":
        raise HTTPException(status_code=400, detail="运行中的策略不能回滚，请先停止")

    result = await db.execute(
        select(StrategyVersion).where(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.version == payload.target_version,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="目标版本不存在")

    strategy.code = target.code
    strategy.params = target.params

    max_ver = await db.scalar(
        select(func.max(StrategyVersion.version)).where(
            StrategyVersion.strategy_id == strategy_id,
        )
    )
    new_ver = (max_ver or 0) + 1
    snapshot = StrategyVersion(
        strategy_id=strategy_id,
        version=new_ver,
        code=strategy.code,
        params=strategy.params,
        change_note=f"回滚到版本 {payload.target_version}",
    )
    db.add(snapshot)
    await db.flush()
    return ResponseBase(data=StrategyVersionResponse.model_validate(snapshot))