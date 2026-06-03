from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    ChangePasswordRequest,
)
from app.services.auth_service import AuthService
from app.services.audit_service import log_action, extract_request_info

router = APIRouter()


@router.post("/register", response_model=ResponseBase[UserResponse], status_code=201)
async def register(payload: RegisterRequest, db: DBSession, request: Request):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次密码不一致")

    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user_count = await db.scalar(select(func.count(User.id)))
    role = "admin" if user_count == 0 else "trader"

    user = User(
        username=payload.username,
        hashed_password=AuthService.hash_password(payload.password),
        role=role,
    )
    db.add(user)
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="auth.register", resource_type="user", resource_id=str(user.id), ip_address=ip, user_agent=ua)

    return ResponseBase(data=UserResponse.model_validate(user))


@router.post("/login", response_model=ResponseBase[TokenResponse])
async def login(payload: LoginRequest, db: DBSession, request: Request):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    ip, ua = extract_request_info(request)

    if user is None:
        await log_action(db, action="auth.login_failed", detail={"reason": "user_not_found", "username": payload.username}, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        await log_action(db, user_id=user.id, action="auth.login_failed", detail={"reason": "account_locked"}, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=423, detail="账号已锁定，请稍后重试")

    if not AuthService.verify_password(payload.password, user.hashed_password):
        user.login_failed_count += 1
        if user.login_failed_count >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db.flush()
        await log_action(db, user_id=user.id, action="auth.login_failed", detail={"reason": "wrong_password"}, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.login_failed_count = 0
    user.locked_until = None
    await db.flush()

    await log_action(db, user_id=user.id, action="auth.login", ip_address=ip, user_agent=ua)

    access_token = AuthService.create_access_token(str(user.id), user.role)
    refresh_token = AuthService.create_refresh_token(str(user.id))
    return ResponseBase(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.post("/refresh", response_model=ResponseBase[TokenResponse])
async def refresh_token(payload: RefreshRequest, db: DBSession):
    token_data = AuthService.decode_token(payload.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = AuthService.create_access_token(str(user.id), user.role)
    refresh_token = AuthService.create_refresh_token(str(user.id))
    return ResponseBase(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.get("/me", response_model=ResponseBase[UserResponse])
async def get_me(user: CurrentUser):
    return ResponseBase(data=UserResponse.model_validate(user))


@router.put("/password", response_model=ResponseBase[None])
async def change_password(
    user: CurrentUser,
    db: DBSession,
    payload: ChangePasswordRequest,
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次密码不一致")
    if not AuthService.verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    user.hashed_password = AuthService.hash_password(payload.new_password)
    await db.flush()
    return ResponseBase()
