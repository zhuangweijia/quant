## Why

系统当前只有注册和登录功能，管理员无法管理其他用户（查看列表、禁用/启用、重置密码、修改角色）。同时系统没有审计日志，敏感操作（登录、策略启停、下单、修改设置等）无法追溯，这在多用户或实盘场景下是合规和运维的硬性需求。

## What Changes

- 新增 `audit_logs` 数据库表，记录用户敏感操作的审计日志
- 新增审计日志自动记录中间件/装饰器，在关键 API 端点自动写入审计记录
- 新增管理员用户管理 API：用户列表、禁用/启用用户、重置密码、修改角色
- 新增管理员审计日志查询 API：分页查询、按用户/操作类型/时间范围过滤
- 在 `deps.py` 中新增 `AdminUser` 依赖，限制管理员路由访问权限

## Capabilities

### New Capabilities
- `admin-user-management`: 管理员对系统用户的 CRUD 管理，包括列表查看、禁用/启用、密码重置、角色变更
- `audit-logging`: 系统审计日志的自动记录与查询，覆盖登录、交易、策略、风控、设置等敏感操作

### Modified Capabilities
<!-- 无现有 specs 需要修改 -->

## Impact

- **数据库变更**: 新增 `audit_logs` 表，需要 Alembic migration
- **新增 API 路由**: `/api/v1/admin/users`（用户管理）、`/api/v1/admin/audit-logs`（审计查询）
- **修改现有文件**: `deps.py`（新增 AdminUser）、`api/v1/__init__.py`（注册新路由）、`api/v1/auth.py`（记录登录审计）
- **新增文件**: `models/audit_log.py`、`schemas/admin.py`、`schemas/audit.py`、`api/v1/admin.py`、`services/audit_service.py`
- **无前端变更**（本次仅后端）
