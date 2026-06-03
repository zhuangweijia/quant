## 1. 数据模型与迁移

- [x] 1.1 创建 `models/audit_log.py`：定义 `AuditLog` 模型，包含 id（UUID）、user_id（FK）、action（String）、resource_type（String）、resource_id（String）、detail（JSONB）、ip_address（String）、user_agent（String）、created_at（DateTime），添加索引 ix_audit_logs_user_created 和 ix_audit_logs_action_created
- [x] 1.2 在 `models/__init__.py` 中导入 AuditLog 确保 Alembic 能检测到
- [x] 1.3 生成 Alembic migration：`alembic revision --autogenerate -m "add audit_logs table"`

## 2. 审计日志服务

- [x] 2.1 创建 `services/audit_service.py`：实现 `log_action(db, user_id, action, resource_type, resource_id, detail, request)` 异步函数，从 request 提取 ip_address 和 user_agent，写入 audit_logs 表
- [x] 2.2 在 `api/v1/auth.py` 的 login、register 端点中添加审计日志调用（`auth.login`、`auth.login_failed`、`auth.register`）
- [x] 2.3 在 `api/v1/trade.py` 的订单提交、撤单、平仓端点中添加审计日志调用（`trade.order_submit`、`trade.order_cancel`、`trade.position_close`）
- [x] 2.4 在 `api/v1/strategy.py` 的创建、启动、停止、删除端点中添加审计日志调用
- [x] 2.5 在 `api/v1/risk.py` 的规则创建、更新、删除端点中添加审计日志调用
- [x] 2.6 在 `api/v1/settings.py` 的券商配置和交易模式端点中添加审计日志调用（注意不记录 API key 等敏感值）

## 3. 管理员权限守卫

- [x] 3.1 在 `api/deps.py` 中新增 `get_admin_user` 依赖：复用 `get_current_user` 后检查 `user.role == "admin"`，否则抛出 403
- [x] 3.2 新增 `AdminUser` 类型别名（`Annotated[User, Depends(get_admin_user)]`）

## 4. 管理员 API - Schemas

- [x] 4.1 创建 `schemas/admin.py`：定义 `AdminUserResponse`（id, username, role, is_active, created_at）、`AdminUserListResponse`（items + pagination）、`ResetPasswordRequest`（new_password + confirm_password）、`ChangeRoleRequest`（role）
- [x] 4.2 创建 `schemas/audit.py`：定义 `AuditLogResponse`（id, user_id, action, resource_type, resource_id, detail, ip_address, user_agent, created_at）、`AuditLogListResponse`（items + pagination）

## 5. 管理员 API - 路由

- [x] 5.1 创建 `api/v1/admin.py`：实现 `GET /admin/users`（分页 + 过滤：role, is_active, keyword）、`PATCH /admin/users/{id}/disable`（禁用，禁止自禁用）、`PATCH /admin/users/{id}/enable`、`POST /admin/users/{id}/reset-password`（密码校验）、`PATCH /admin/users/{id}/role`（禁止自改角色）
- [x] 5.2 实现 `GET /admin/audit-logs`（分页 + 过滤：user_id, action, start_time, end_time，按 created_at 降序）
- [x] 5.3 所有管理员端点使用 `AdminUser` 依赖守卫
- [x] 5.4 在管理员用户管理操作中添加审计日志调用（`admin.user_disable`、`admin.user_enable`、`admin.user_password_reset`、`admin.user_role_change`）
- [x] 5.5 在 `api/v1/__init__.py` 中注册 admin 路由：`router.include_router(admin.router, prefix="/admin", tags=["管理"])`

## 6. 验证

- [x] 6.1 验证所有新建文件 Python 语法正确
- [x] 6.2 验证 Alembic migration 文件生成正确
