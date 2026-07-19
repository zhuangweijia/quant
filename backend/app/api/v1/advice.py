from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.advice import AdviceTodayResponse, DailyAdviceResponse
from app.schemas.common import ResponseBase
from app.services import advice_service

router = APIRouter()


@router.get("/today", response_model=ResponseBase[AdviceTodayResponse])
async def get_today_advice(user: CurrentUser, db: DBSession):
    return ResponseBase(data=await advice_service.get_today_state(db, user.id))


@router.post("/generate", response_model=ResponseBase[DailyAdviceResponse])
async def generate_advice(
    user: CurrentUser,
    db: DBSession,
    force: bool = Query(default=False),
):
    signal_date = await advice_service.latest_ranked_signal_date(db)
    if signal_date is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ranked_predictions_missing",
                "message": advice_service.ERROR_MESSAGES["ranked_predictions_missing"],
            },
        )
    advice = await advice_service.generate_for_user(
        db, user.id, signal_date, force=force
    )
    return ResponseBase(data=await advice_service.get_advice_response(db, advice))
