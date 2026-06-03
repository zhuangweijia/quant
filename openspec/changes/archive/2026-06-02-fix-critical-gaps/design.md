## Context

QuantPlatform 是一个基于 FastAPI + Vue 3 的量化交易平台。系统当前整体完成度约 70%，核心交易闭环已通，但存在 2 个致命 Bug（回测崩溃、Alpaca 下单失败）和 6 项"配置幻觉"问题（配置项已定义但无实现代码）。这些问题阻塞了生产部署。

关键约束：
- 后端为 async FastAPI，使用 APScheduler 做定时任务
- Redis 已部署，可用于限流计数器
- 数据库为 PostgreSQL 16，已有 `settings` 表存储系统参数
- 不引入新的 pip 依赖

## Goals / Non-Goals

**Goals:**
- 修复 2 个 P0 致命 Bug，使回测和美股实盘下单正常工作
- 消除 PaperBroker 跨用户状态泄漏
- 实现 6 项"配置幻觉"功能，使配置项真正生效
- 不引入新的外部依赖

**Non-Goals:**
- 不新增管理员用户管理 API（独立 change）
- 不新增审计日志系统（独立 change）
- 不修改数据库 schema（无需 migration）
- 不修改前端代码
- 不引入 2FA/MFA
- 不实现测试覆盖（独立 change）

## Decisions

### D1: 回测指标计算 — 直接补全计算逻辑

**选择**: 在 `_execute_backtest` 函数中补全 `sortino`、`calmar`、`monthly_summary` 的计算。

**理由**: Sharpe ratio 已经用纯 Python + math 计算，保持一致风格。不引入 numpy/pandas 避免增加依赖和回测沙箱复杂度。

**Sortino 公式**: `avg_return / downside_deviation * sqrt(252)`，downside_deviation 只取负收益的标准差。
**Calmar 公式**: `annual_return / max_drawdown`（当 max_drawdown > 0 时）。
**Monthly returns**: 从 equity_curve 按年月分组，计算相邻月末权益的变化率。

### D2: Alpaca 返回类型 — 修改 AlpacaBroker 对齐基类

**选择**: 修改 `AlpacaBroker._submit_order_sync` 和 `cancel_order` 返回 dict，与 `BrokerAdapter` 接口对齐。

**不选择**: 修改 `order_manager.py` 适配 str 返回 — 因为基类契约是 dict，PaperBroker 和 BinanceBroker 都返回 dict，不应为了一个实现破坏多态。

**具体变更**:
- `_submit_order_sync`: 返回 `{"broker_order_id": str, "status": str, "filled_qty": Decimal, "filled_price": Decimal|None, "commission": Decimal}`
- `cancel_order`: 返回 `{"status": "cancelled"}` 或 `{"status": "error", "reason": str}`
- 顺带增加 stop order 支持（当前只支持 market/limit）

### D3: PaperBroker 隔离 — 按 user_id 缓存实例

**选择**: 在 `broker_factory.py` 的 `_broker_cache` 中按 `paper:{user_id}` 缓存 PaperBroker 实例。

**不选择**: 保持全局单例 — 跨用户状态泄漏是真实 bug；也不选择每次创建新实例 — 会丢失 pending/submitted 状态的模拟订单。

### D4: 限流 — 基于内存的滑动窗口中间件

**选择**: 实现 Starlette `BaseHTTPMiddleware`，使用内存字典做滑动窗口计数。

**不选择**: 
- Redis 限流 — 增加复杂度，单实例部署无需分布式限流
- `slowapi` 库 — 引入新依赖

**规则**:
- 默认: 60 次/分钟/IP 或 user_id
- 交易路由 (`/api/v1/trade/`): 10 次/分钟
- 回测路由 (`/api/v1/backtest/run`): 3 次/分钟
- 响应头: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### D5: 回测并发与超时 — asyncio.Semaphore + asyncio.timeout

**选择**: 模块级 `asyncio.Semaphore(3)` 控制并发，`asyncio.timeout(600)` 控制超时。

**理由**: 最简实现，无额外依赖。超时后 asyncio 会取消 task，异常处理中标记 result 为 failed。

### D6: 权益快照 — APScheduler cron job

**选择**: 在 `strategy_engine.start()` 中注册 cron job，每日 15:30 执行 `save_equity_snapshot`。

**理由**: 复用现有 APScheduler 实例和 `save_equity_snapshot` 函数，仅需注册。

### D7: 数据清理 — 独立 cleanup_service + cron job

**选择**: 新建 `services/cleanup_service.py`，从 `settings` 表读取保留天数，批量删除过期记录。每日 03:00 执行。

**不选择**: 直接在 strategy_engine 中写清理逻辑 — 保持职责分离，cleanup_service 可独立测试和调用。

**清理范围**: `strategy_logs`、`alerts`、`notification_logs`、`market_data`（按各自 `created_at` 与 `retention_days` 设置比较）。

## Risks / Trade-offs

- **内存限流在多进程部署下失效** → 当前为单实例 Docker 部署，可接受；如未来水平扩展需迁移到 Redis
- **回测超时使用 `asyncio.timeout`（Python 3.11+）** → 需确认部署环境 Python 版本 >= 3.11，否则改用 `asyncio.wait_for`
- **数据清理大批量删除可能锁表** → 使用分批删除（每批 5000 条），避免长事务
- **PaperBroker 按用户缓存后内存增长** → 单实例用户量有限，且 `_orders` 中已完成订单无状态查询，可在 cleanup 中一并清理
