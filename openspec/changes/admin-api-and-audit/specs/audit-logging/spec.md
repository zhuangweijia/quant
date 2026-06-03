## ADDED Requirements

### Requirement: Audit log data model
系统 SHALL 在 `audit_logs` 表中存储审计记录，每条记录包含 `id`、`user_id`、`action`、`resource_type`、`resource_id`、`detail`（JSONB）、`ip_address`、`user_agent`、`created_at`。

#### Scenario: Audit log record structure
- **WHEN** 系统记录一条审计日志
- **THEN** 该记录包含操作者 user_id、标准化的 action 字符串、资源类型和 ID、结构化 detail、客户端 IP 和 User-Agent

### Requirement: Login and auth audit logging
系统 SHALL 在用户登录（成功和失败）以及注册时自动记录审计日志。

#### Scenario: Successful login audit
- **WHEN** 用户登录成功
- **THEN** 系统记录一条 action 为 `auth.login` 的审计日志，detail 包含登录方式

#### Scenario: Failed login audit
- **WHEN** 用户登录失败（密码错误或账号锁定）
- **THEN** 系统记录一条 action 为 `auth.login_failed` 的审计日志，detail 包含失败原因

#### Scenario: User registration audit
- **WHEN** 新用户注册成功
- **THEN** 系统记录一条 action 为 `auth.register` 的审计日志

### Requirement: Trade audit logging
系统 SHALL 在订单提交、撤单、平仓时记录审计日志。

#### Scenario: Order submitted audit
- **WHEN** 用户提交订单
- **THEN** 系统记录 action 为 `trade.order_submit`，detail 包含 symbol、side、order_type、qty、price

#### Scenario: Order cancelled audit
- **WHEN** 用户撤销订单
- **THEN** 系统记录 action 为 `trade.order_cancel`，detail 包含 order_id

#### Scenario: Position closed audit
- **WHEN** 用户平仓
- **THEN** 系统记录 action 为 `trade.position_close`，detail 包含 symbol、qty

### Requirement: Strategy audit logging
系统 SHALL 在策略创建、启动、停止、删除时记录审计日志。

#### Scenario: Strategy created audit
- **WHEN** 用户创建新策略
- **THEN** 系统记录 action 为 `strategy.create`，detail 包含 strategy_id、strategy_name

#### Scenario: Strategy started audit
- **WHEN** 用户启动策略
- **THEN** 系统记录 action 为 `strategy.start`

#### Scenario: Strategy stopped audit
- **WHEN** 用户停止策略
- **THEN** 系统记录 action 为 `strategy.stop`

#### Scenario: Strategy deleted audit
- **WHEN** 用户删除策略
- **THEN** 系统记录 action 为 `strategy.delete`

### Requirement: Risk rule audit logging
系统 SHALL 在风控规则创建、更新、删除时记录审计日志。

#### Scenario: Risk rule created audit
- **WHEN** 用户创建风控规则
- **THEN** 系统记录 action 为 `risk.rule_create`，detail 包含 rule_type

#### Scenario: Risk rule updated audit
- **WHEN** 用户更新风控规则
- **THEN** 系统记录 action 为 `risk.rule_update`

#### Scenario: Risk rule deleted audit
- **WHEN** 用户删除风控规则
- **THEN** 系统记录 action 为 `risk.rule_delete`

### Requirement: Settings audit logging
系统 SHALL 在修改券商配置和交易模式时记录审计日志。

#### Scenario: Broker config updated audit
- **WHEN** 用户更新券商配置
- **THEN** 系统记录 action 为 `settings.broker_update`，detail 包含 broker_name（不记录 API key 等敏感值）

#### Scenario: Trading mode changed audit
- **WHEN** 用户切换交易模式
- **THEN** 系统记录 action 为 `settings.trading_mode_change`，detail 包含旧模式和新模式

### Requirement: Admin audit log query
系统 SHALL 提供管理员接口 `GET /api/v1/admin/audit-logs`，支持分页查询审计日志。

#### Scenario: Query with pagination
- **WHEN** 管理员发送 `GET /api/v1/admin/audit-logs?page=1&page_size=20`
- **THEN** 系统返回审计日志列表及分页信息，按 created_at 降序排列

#### Scenario: Filter by user
- **WHEN** 管理员发送 `GET /api/v1/admin/audit-logs?user_id=<uuid>`
- **THEN** 系统仅返回该用户的审计日志

#### Scenario: Filter by action
- **WHEN** 管理员发送 `GET /api/v1/admin/audit-logs?action=trade.order_submit`
- **THEN** 系统仅返回该 action 类型的审计日志

#### Scenario: Filter by time range
- **WHEN** 管理员发送 `GET /api/v1/admin/audit-logs?start_time=2026-01-01&end_time=2026-06-01`
- **THEN** 系统仅返回该时间范围内的审计日志

### Requirement: Audit log immutability
审计日志 SHALL 为只读，一旦写入不可修改或删除。

#### Scenario: No update or delete API
- **WHEN** 任何用户尝试修改或删除审计日志
- **THEN** 无对应 API 可用（系统不提供审计日志的 PUT/DELETE/PATCH 端点）
