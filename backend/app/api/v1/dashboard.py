"""Dashboard API — stub implementation.

Full implementation in task group 11 (dashboard rework).
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase

router = APIRouter()


@router.get("/overview", response_model=ResponseBase[dict])
async def get_overview(user: CurrentUser, db: DBSession):
    return ResponseBase(data={"message": "Dashboard pending rework"})
