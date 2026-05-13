from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase

router = APIRouter()

_DEFAULT_PARAMS = {
    "max_strategies_per_user": "50",
    "max_running_strategies": "10",
    "max_concurrent_backtests": "3",
    "backtest_timeout": "600",
    "order_timeout": "30",
    "paper_initial_capital": "1000000",
    "default_commission_a_stock": "0.00025",
    "default_commission_us_stock": "0.005",
    "default_commission_crypto": "0.001",
    "data_retention_days": "30",
    "alert_retention_days": "90",
}


class BrokerConfigRequest(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    params: dict | None = None


class TradingModeRequest(BaseModel):
    mode: str
    password: str | None = None


class NotificationConfigRequest(BaseModel):
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 465
    email_sender: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_recipient: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    notify_levels: list[str] = ["warning", "error"]


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class SystemParamsRequest(BaseModel):
    params: dict


@router.get("/brokers", response_model=ResponseBase[list[dict]])
async def get_brokers(user: CurrentUser, db: DBSession):
    brokers = [
        {
            "broker_name": "binance",
            "market": "crypto",
            "api_key": "",
            "has_secret": False,
            "params": {"network": "mainnet"},
            "connected": False,
        },
        {
            "broker_name": "alpaca",
            "market": "us_stock",
            "api_key": "",
            "has_secret": False,
            "params": {"environment": "paper"},
            "connected": False,
        },
        {
            "broker_name": "akshare",
            "market": "a_stock",
            "api_key": "",
            "has_secret": False,
            "params": {},
            "connected": True,
        },
    ]
    return ResponseBase(data=brokers)


@router.put("/brokers/{broker_name}", response_model=ResponseBase[dict])
async def save_broker_config(
    user: CurrentUser, db: DBSession, broker_name: str, payload: BrokerConfigRequest
):
    if broker_name not in ("binance", "alpaca", "akshare"):
        raise HTTPException(status_code=400, detail="不支持的交易所")
    return ResponseBase(data={"broker_name": broker_name, "saved": True})


@router.post("/brokers/{broker_name}/test", response_model=ResponseBase[dict])
async def test_broker_connection(user: CurrentUser, db: DBSession, broker_name: str):
    return ResponseBase(data={"connected": broker_name == "akshare"})


@router.get("/trading-mode", response_model=ResponseBase[dict])
async def get_trading_mode(user: CurrentUser, db: DBSession):
    from app.services.account_service import get_or_create_account
    account = await get_or_create_account(db, user.id)
    return ResponseBase(data={"mode": account.mode})


@router.put("/trading-mode", response_model=ResponseBase[dict])
async def set_trading_mode(user: CurrentUser, db: DBSession, payload: TradingModeRequest):
    if payload.mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="无效的交易模式")
    if payload.mode == "live" and not payload.password:
        raise HTTPException(status_code=400, detail="切换到实盘需要输入密码验证")

    if payload.password:
        from app.services.auth_service import AuthService
        from app.models.user import User
        db_user = await db.get(User, user.id)
        if not db_user or not AuthService.verify_password(payload.password, db_user.hashed_password):
            raise HTTPException(status_code=400, detail="密码不正确")

    from app.services.account_service import get_or_create_account
    account = await get_or_create_account(db, user.id)
    account.mode = payload.mode
    await db.flush()
    return ResponseBase(data={"mode": account.mode})


@router.get("/notifications", response_model=ResponseBase[dict])
async def get_notifications(user: CurrentUser, db: DBSession):
    return ResponseBase(data={
        "email_enabled": False,
        "email_smtp_host": "",
        "email_smtp_port": 465,
        "email_sender": "",
        "has_email_password": False,
        "email_use_ssl": True,
        "email_recipient": "",
        "webhook_enabled": False,
        "webhook_url": "",
        "has_webhook_secret": False,
        "notify_levels": ["warning", "error"],
    })


@router.put("/notifications", response_model=ResponseBase[dict])
async def save_notifications(user: CurrentUser, db: DBSession, payload: NotificationConfigRequest):
    return ResponseBase(data={"saved": True})


@router.post("/notifications/test-email", response_model=ResponseBase[dict])
async def test_email(user: CurrentUser, db: DBSession):
    return ResponseBase(data={"sent": False, "message": "SMTP 未配置"})


@router.post("/notifications/test-webhook", response_model=ResponseBase[dict])
async def test_webhook(user: CurrentUser, db: DBSession):
    return ResponseBase(data={"sent": False, "message": "Webhook 未配置"})


@router.get("/params", response_model=ResponseBase[dict])
async def get_params(user: CurrentUser, db: DBSession):
    return ResponseBase(data=_DEFAULT_PARAMS)


@router.put("/params", response_model=ResponseBase[dict])
async def save_params(user: CurrentUser, db: DBSession, payload: SystemParamsRequest):
    return ResponseBase(data=payload.params)


@router.post("/params/reset", response_model=ResponseBase[dict])
async def reset_params(user: CurrentUser, db: DBSession):
    return ResponseBase(data=_DEFAULT_PARAMS)


@router.get("/profile", response_model=ResponseBase[dict])
async def get_profile(user: CurrentUser, db: DBSession):
    return ResponseBase(data={
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": str(user.created_at) if hasattr(user, "created_at") else "",
    })


@router.put("/password", response_model=ResponseBase[None])
async def change_password(user: CurrentUser, db: DBSession, payload: PasswordChangeRequest):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="密码至少8位")
    if not any(c.isalpha() for c in payload.new_password) or not any(c.isdigit() for c in payload.new_password):
        raise HTTPException(status_code=400, detail="密码需包含字母和数字")
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次密码不一致")

    from app.services.auth_service import AuthService
    from app.models.user import User
    db_user = await db.get(User, user.id)
    if not db_user or not AuthService.verify_password(payload.old_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码不正确")

    db_user.hashed_password = AuthService.hash_password(payload.new_password)
    await db.flush()
    return ResponseBase()
