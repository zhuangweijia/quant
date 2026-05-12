from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.backtest import BacktestRunRequest

router = APIRouter()


@router.post("/run", response_model=ResponseBase[dict])
async def run_backtest(user: CurrentUser, db: DBSession, payload: BacktestRunRequest):
    return ResponseBase(data={}, message="回测模块待实现")


@router.get("/results", response_model=ResponseBase[list[dict]])
async def list_results(user: CurrentUser, db: DBSession):
    return ResponseBase(data=[], message="回测模块待实现")


@router.get("/results/{result_id}", response_model=ResponseBase[dict])
async def get_result(user: CurrentUser, db: DBSession, result_id: str):
    return ResponseBase(data={}, message="回测模块待实现")
