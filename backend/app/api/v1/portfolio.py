from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.schemas.portfolio import (
    InvestmentProfileInput,
    InvestmentProfileResponse,
    PortfolioResponse,
    PortfolioSetupRequest,
    PortfolioSetupStatus,
)
from app.services import portfolio_service
from app.services.audit_service import extract_request_info

router = APIRouter()


@router.get("/setup-status", response_model=ResponseBase[PortfolioSetupStatus])
async def setup_status(user: CurrentUser, db: DBSession):
    return ResponseBase(data=await portfolio_service.get_setup_status(db, user.id))


@router.post("/setup", response_model=ResponseBase[PortfolioResponse])
async def setup_portfolio(
    user: CurrentUser,
    db: DBSession,
    payload: PortfolioSetupRequest,
    request: Request,
):
    return ResponseBase(
        data=await portfolio_service.complete_setup(
            db, user.id, payload, extract_request_info(request)
        )
    )


@router.get("", response_model=ResponseBase[PortfolioResponse])
async def get_portfolio(user: CurrentUser, db: DBSession):
    return ResponseBase(data=await portfolio_service.get_portfolio_response(db, user.id))


@router.put("/profile", response_model=ResponseBase[InvestmentProfileResponse])
async def update_profile(
    user: CurrentUser,
    db: DBSession,
    payload: InvestmentProfileInput,
    request: Request,
):
    return ResponseBase(
        data=await portfolio_service.create_profile_version(
            db, user.id, payload, extract_request_info(request)
        )
    )
