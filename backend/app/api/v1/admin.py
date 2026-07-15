from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, select

from app.api.deps import AdminUser, DBSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import (
    AdminUserListResponse,
    AdminUserResponse,
    ChangeRoleRequest,
    ResetPasswordRequest,
)
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.schemas.common import ResponseBase
from app.services.audit_service import extract_request_info, log_action

router = APIRouter()


@router.get("/users", response_model=ResponseBase[AdminUserListResponse])
async def list_users(
    admin: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    keyword: str | None = Query(None),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    if keyword:
        query = query.where(User.username.ilike(f"%{keyword}%"))
        count_query = count_query.where(User.username.ilike(f"%{keyword}%"))

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=AdminUserListResponse(
            items=[AdminUserResponse.model_validate(u) for u in users],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.patch("/users/{user_id}/disable", response_model=ResponseBase[AdminUserResponse])
async def disable_user(
    admin: AdminUser,
    db: DBSession,
    user_id: UUID,
    request: Request,
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="不能禁用自己")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = False
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=admin.id,
        action="admin.user_disable",
        resource_type="user",
        resource_id=str(user_id),
        detail={"username": user.username},
        ip_address=ip,
        user_agent=ua,
    )

    return ResponseBase(data=AdminUserResponse.model_validate(user))


@router.patch("/users/{user_id}/enable", response_model=ResponseBase[AdminUserResponse])
async def enable_user(
    admin: AdminUser,
    db: DBSession,
    user_id: UUID,
    request: Request,
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = True
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=admin.id,
        action="admin.user_enable",
        resource_type="user",
        resource_id=str(user_id),
        detail={"username": user.username},
        ip_address=ip,
        user_agent=ua,
    )

    return ResponseBase(data=AdminUserResponse.model_validate(user))


@router.post("/users/{user_id}/reset-password", response_model=ResponseBase[None])
async def reset_password(
    admin: AdminUser,
    db: DBSession,
    user_id: UUID,
    payload: ResetPasswordRequest,
    request: Request,
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次密码不一致")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    from app.services.auth_service import AuthService

    user.hashed_password = AuthService.hash_password(payload.new_password)
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=admin.id,
        action="admin.user_password_reset",
        resource_type="user",
        resource_id=str(user_id),
        detail={"username": user.username},
        ip_address=ip,
        user_agent=ua,
    )

    return ResponseBase()


@router.patch("/users/{user_id}/role", response_model=ResponseBase[AdminUserResponse])
async def change_role(
    admin: AdminUser,
    db: DBSession,
    user_id: UUID,
    payload: ChangeRoleRequest,
    request: Request,
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_role = user.role
    user.role = payload.role
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=admin.id,
        action="admin.user_role_change",
        resource_type="user",
        resource_id=str(user_id),
        detail={"username": user.username, "old_role": old_role, "new_role": payload.role},
        ip_address=ip,
        user_agent=ua,
    )

    return ResponseBase(data=AdminUserResponse.model_validate(user))


@router.get("/audit-logs", response_model=ResponseBase[AuditLogListResponse])
async def list_audit_logs(
    admin: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
):
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if start_time:
        query = query.where(AuditLog.created_at >= start_time)
        count_query = count_query.where(AuditLog.created_at >= start_time)
    if end_time:
        query = query.where(AuditLog.created_at <= end_time)
        count_query = count_query.where(AuditLog.created_at <= end_time)

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=AuditLogListResponse(
            items=[AuditLogResponse.model_validate(l) for l in logs],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )
