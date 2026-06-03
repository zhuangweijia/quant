## ADDED Requirements

### Requirement: Admin user list
系统 SHALL 提供管理员接口 `GET /api/v1/admin/users`，返回分页的用户列表，支持按角色、状态、用户名过滤。

#### Scenario: List all users with pagination
- **WHEN** 管理员发送 `GET /api/v1/admin/users?page=1&page_size=20`
- **THEN** 系统返回用户列表（id, username, role, is_active, created_at）及分页信息（total, page, page_size），不包含密码字段

#### Scenario: Filter by role
- **WHEN** 管理员发送 `GET /api/v1/admin/users?role=trader`
- **THEN** 系统仅返回 role 为 trader 的用户

#### Scenario: Filter by active status
- **WHEN** 管理员发送 `GET /api/v1/admin/users?is_active=false`
- **THEN** 系统仅返回已禁用的用户

#### Scenario: Search by username
- **WHEN** 管理员发送 `GET /api/v1/admin/users?keyword=john`
- **THEN** 系统返回用户名包含 "john" 的用户（模糊匹配）

### Requirement: Admin disable user
系统 SHALL 提供管理员接口 `PATCH /api/v1/admin/users/{id}/disable`，禁用指定用户。

#### Scenario: Disable an active user
- **WHEN** 管理员发送 `PATCH /api/v1/admin/users/{id}/disable`
- **THEN** 目标用户的 `is_active` 设为 `false`，已发放的 JWT 在后续请求中因 `is_active` 检查失效

#### Scenario: Disable self forbidden
- **WHEN** 管理员尝试禁用自己的账号
- **THEN** 系统返回 400 错误，提示不能禁用自己

### Requirement: Admin enable user
系统 SHALL 提供管理员接口 `PATCH /api/v1/admin/users/{id}/enable`，启用指定用户。

#### Scenario: Enable a disabled user
- **WHEN** 管理员发送 `PATCH /api/v1/admin/users/{id}/enable`
- **THEN** 目标用户的 `is_active` 设为 `true`

### Requirement: Admin reset user password
系统 SHALL 提供管理员接口 `POST /api/v1/admin/users/{id}/reset-password`，重置指定用户的密码。

#### Scenario: Reset password successfully
- **WHEN** 管理员发送 `POST /api/v1/admin/users/{id}/reset-password` 并提供 `new_password`
- **THEN** 目标用户的密码被更新为 `new_password` 的哈希值

#### Scenario: Reset password validation
- **WHEN** 管理员提供的 `new_password` 不满足最小长度要求（8 位）
- **THEN** 系统返回 422 验证错误

### Requirement: Admin change user role
系统 SHALL 提供管理员接口 `PATCH /api/v1/admin/users/{id}/role`，修改指定用户的角色。

#### Scenario: Change role successfully
- **WHEN** 管理员发送 `PATCH /api/v1/admin/users/{id}/role` 并提供 `role`（admin 或 trader）
- **THEN** 目标用户的 role 被更新

#### Scenario: Change own role forbidden
- **WHEN** 管理员尝试修改自己的角色
- **THEN** 系统返回 400 错误，提示不能修改自己的角色

### Requirement: Admin access control
系统 SHALL 限制所有 `/api/v1/admin/` 路径下的接口仅允许 role 为 admin 的用户访问。

#### Scenario: Trader access denied
- **WHEN** role 为 trader 的用户请求 `/api/v1/admin/users`
- **THEN** 系统返回 403 Forbidden

#### Scenario: Anonymous access denied
- **WHEN** 未认证用户请求 `/api/v1/admin/users`
- **THEN** 系统返回 401 Unauthorized
