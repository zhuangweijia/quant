## Context

QuantPlatform 使用 FastAPI + PostgreSQL + SQLAlchemy async。当前认证系统基于 JWT RS256，`User` 模型已有 `role`（admin/trader）和 `is_active` 字段，但没有管理员管理 API。`deps.py` 有 `CurrentUser` 依赖但无角色检查。系统没有任何审计日志机制。

## Goals / Non-Goals

**Goals:**
- 管理员可以通过 API 管理所有用户（查看、禁用/启用、重置密码、改角色）
- 系统自动记录关键敏感操作到审计日志
- 管理员可以查询审计日志（分页、过滤）
- 管理员权限通过路由级别守卫强制执行

**Non-Goals:**
- 不实现前端管理页面（仅后端 API）
- 不实现实时审计日志推送（WebSocket）
- 不实现审计日志的自动清理（已有 data-cleanup 覆盖）
- 不修改现有认证流程（JWT 机制不变）
- 不实现细粒度权限（RBAC），只区分 admin/trader

## Decisions

### D1: 审计日志存储 — 独立 audit_logs 表

**选择**: 新增 `audit_logs` 表，字段包括 `user_id`、`action`、`resource_type`、`resource_id`、`detail`（JSONB）、`ip_address`、`user_agent`、`created_at`。

**不选择**: 
- 写入文件日志 — 无法高效查询和过滤
- 写入 Redis — 数据易失，不适合审计场景

**理由**: PostgreSQL JSONB 支持灵活的 detail 查询，且已有成熟的 SQLAlchemy async 模式。`audit_logs` 只追加不修改，查询走索引即可。

### D2: 审计日志记录方式 — 装饰器 + 手动调用混合

**选择**: 
- 在关键路由处理函数中手动调用 `audit_service.log_action()` 记录
- 不用中间件（中间件无法感知业务语义，无法记录 action/resource 等结构化信息）

**理由**: 审计日志的核心价值在于结构化的 action 和 resource 信息，中间件只能记录 HTTP 级别的请求/响应，无法提取业务语义。

### D3: 管理员权限守卫 — 新增 AdminUser 依赖

**选择**: 在 `deps.py` 中新增 `get_admin_user` 依赖，复用 `get_current_user` 后检查 `user.role == "admin"`。

**不选择**: 中间件拦截 — 路由级别守卫更灵活，可以精确控制哪些端点需要管理员权限。

### D4: 审计日志的 action 分类

定义标准 action 枚举：

| 分类 | action 值 | 触发点 |
|------|-----------|--------|
| 认证 | `auth.login`、`auth.login_failed`、`auth.register` | auth.py |
| 用户管理 | `admin.user_disable`、`admin.user_enable`、`admin.user_role_change`、`admin.user_password_reset` | admin.py |
| 交易 | `trade.order_submit`、`trade.order_cancel`、`trade.position_close` | trade.py |
| 策略 | `strategy.create`、`strategy.start`、`strategy.stop`、`strategy.delete` | strategy.py |
| 风控 | `risk.rule_create`、`risk.rule_update`、`risk.rule_delete` | risk.py |
| 设置 | `settings.broker_update`、`settings.trading_mode_change` | settings.py |

### D5: 用户列表 API — 分页 + 过滤

**选择**: 支持分页（page/page_size）、按角色过滤、按状态过滤、按用户名搜索。不暴露密码相关字段。

### D6: 重置密码 — 管理员直接设置新密码

**选择**: 管理员提供新密码，系统直接设置。不需要发送邮件或短信验证码。

**理由**: 当前系统无邮件验证机制，管理员重置密码是最简方案。未来可扩展为发送临时密码邮件。

## Risks / Trade-offs

- **审计日志写入增加 DB 负载** → 每次写入是一行 INSERT，开销极小；可后续优化为批量写入或异步队列
- **audit_logs 表会持续增长** → 已有 data-cleanup 机制覆盖，保留天数可配置
- **管理员重置密码无二次验证** → 管理员本身已通过 JWT 认证，属于可接受风险
- **无审计日志防篡改机制** → 当前阶段不做哈希链签名，后续如有合规需求可引入
