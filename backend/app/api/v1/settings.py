from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ResponseBase
from app.services.audit_service import log_action, extract_request_info

router = APIRouter()


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
    from app.services.settings_service import get_settings_category
    binance_config = await get_settings_category(db, user.id, "broker:binance")
    alpaca_config = await get_settings_category(db, user.id, "broker:alpaca")

    import json
    binance_extra = binance_config.get("extra_params", "{}")
    try:
        binance_params = json.loads(binance_extra) if isinstance(binance_extra, str) else binance_extra
    except (json.JSONDecodeError, TypeError):
        binance_params = {}

    brokers = [
        {
            "broker_name": "binance",
            "market": "crypto",
            "api_key": binance_config.get("api_key") or "",
            "has_secret": bool(binance_config.get("api_secret")),
            "params": {
                "testnet": binance_params.get("testnet", False),
                "network": binance_params.get("network", "mainnet"),
            },
            "connected": False,
        },
        {
            "broker_name": "alpaca",
            "market": "us_stock",
            "api_key": alpaca_config.get("api_key") or "",
            "has_secret": bool(alpaca_config.get("api_secret")),
            "params": {"environment": alpaca_config.get("environment", "paper")},
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
    user: CurrentUser, db: DBSession, broker_name: str, payload: BrokerConfigRequest, request: Request
):
    if broker_name not in ("binance", "alpaca", "akshare"):
        raise HTTPException(status_code=400, detail="不支持的交易所")

    from app.services.settings_service import set_setting
    category = f"broker:{broker_name}"
    if payload.api_key:
        await set_setting(db, user.id, category, "api_key", payload.api_key, encrypted=True)
    if payload.api_secret:
        await set_setting(db, user.id, category, "api_secret", payload.api_secret, encrypted=True)
    if payload.params:
        import json
        await set_setting(db, user.id, category, "extra_params", json.dumps(payload.params))

    from app.services.trade.broker_factory import invalidate_broker_cache
    invalidate_broker_cache(user.id, broker_name)

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="settings.broker_update", resource_type="broker", resource_id=broker_name, detail={"broker_name": broker_name}, ip_address=ip, user_agent=ua)

    return ResponseBase(data={"broker_name": broker_name, "saved": True})


@router.post("/brokers/{broker_name}/test", response_model=ResponseBase[dict])
async def test_broker_connection(user: CurrentUser, db: DBSession, broker_name: str):
    if broker_name not in ("binance", "alpaca", "akshare"):
        raise HTTPException(status_code=400, detail="不支持的交易所")

    from app.services.trade.broker_factory import test_broker_connection as do_test
    result = await do_test(db, user.id, broker_name)
    return ResponseBase(data=result)


@router.get("/trading-mode", response_model=ResponseBase[dict])
async def get_trading_mode(user: CurrentUser, db: DBSession):
    from app.services.account_service import get_or_create_account
    account = await get_or_create_account(db, user.id)
    return ResponseBase(data={"mode": account.mode})


@router.put("/trading-mode", response_model=ResponseBase[dict])
async def set_trading_mode(user: CurrentUser, db: DBSession, payload: TradingModeRequest, request: Request):
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
    old_mode = account.mode
    account.mode = payload.mode
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="settings.trading_mode_change", detail={"old_mode": old_mode, "new_mode": payload.mode}, ip_address=ip, user_agent=ua)

    return ResponseBase(data={"mode": account.mode})


@router.get("/notifications", response_model=ResponseBase[dict])
async def get_notifications(user: CurrentUser, db: DBSession):
    from app.services.settings_service import get_settings_category
    config = await get_settings_category(db, user.id, "notification")
    return ResponseBase(data={
        "email_enabled": config.get("email_enabled", "false").lower() == "true",
        "email_smtp_host": config.get("email_smtp_host", ""),
        "email_smtp_port": int(config.get("email_smtp_port", "465")),
        "email_sender": config.get("email_sender", ""),
        "has_email_password": bool(config.get("email_password")),
        "email_use_ssl": config.get("email_use_ssl", "true").lower() == "true",
        "email_recipient": config.get("email_recipient", ""),
        "webhook_enabled": config.get("webhook_enabled", "false").lower() == "true",
        "webhook_url": config.get("webhook_url", ""),
        "has_webhook_secret": bool(config.get("webhook_secret")),
        "notify_levels": config.get("notify_levels", "warning,error").split(","),
    })


@router.put("/notifications", response_model=ResponseBase[dict])
async def save_notifications(user: CurrentUser, db: DBSession, payload: NotificationConfigRequest):
    from app.services.settings_service import set_setting
    pairs = {
        "email_enabled": str(payload.email_enabled).lower(),
        "email_smtp_host": payload.email_smtp_host,
        "email_smtp_port": str(payload.email_smtp_port),
        "email_sender": payload.email_sender,
        "email_use_ssl": str(payload.email_use_ssl).lower(),
        "email_recipient": payload.email_recipient,
        "webhook_enabled": str(payload.webhook_enabled).lower(),
        "webhook_url": payload.webhook_url,
        "notify_levels": ",".join(payload.notify_levels),
    }
    for key, value in pairs.items():
        await set_setting(db, user.id, "notification", key, value)

    if payload.email_password:
        await set_setting(db, user.id, "notification", "email_password", payload.email_password, encrypted=True)
    if payload.webhook_secret:
        await set_setting(db, user.id, "notification", "webhook_secret", payload.webhook_secret, encrypted=True)

    return ResponseBase(data={"saved": True})


@router.post("/notifications/test-email", response_model=ResponseBase[dict])
async def test_email(user: CurrentUser, db: DBSession):
    from app.services.notification_service import send_email
    success = await send_email(db, user.id, "QuantPlatform 测试邮件", "<h2>测试成功</h2><p>邮件通知配置正常。</p>")
    return ResponseBase(data={"sent": success})


@router.post("/notifications/test-webhook", response_model=ResponseBase[dict])
async def test_webhook(user: CurrentUser, db: DBSession):
    from app.services.notification_service import send_webhook
    success = await send_webhook(db, user.id, "test", {"message": "QuantPlatform Webhook 测试"})
    return ResponseBase(data={"sent": success})


@router.get("/params", response_model=ResponseBase[dict])
async def get_params(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import get_system_params
    params = await get_system_params(db)
    return ResponseBase(data=params)


@router.put("/params", response_model=ResponseBase[dict])
async def save_params(user: CurrentUser, db: DBSession, payload: SystemParamsRequest):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import save_system_params
    params = await save_system_params(db, payload.params)
    return ResponseBase(data=params)


@router.post("/params/reset", response_model=ResponseBase[dict])
async def reset_params(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import reset_system_params
    params = await reset_system_params(db)
    return ResponseBase(data=params)


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
