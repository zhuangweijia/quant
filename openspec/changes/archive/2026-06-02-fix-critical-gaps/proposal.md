## Why

系统存在多个致命 Bug 和"配置幻觉"问题：回测引擎因未定义变量在每次完成时崩溃（NameError），Alpaca 券商适配器返回类型与基类不匹配导致美股下单报错，PaperBroker 单例跨用户共享状态存在泄漏风险。此外还有 6 项配置已定义但从未实现的功能（限流、回测并发/超时控制、数据清理、权益快照调度、订单超时），给运维造成"已实现"的错觉。这些问题不修复，系统无法安全投入生产使用。

## What Changes

- 修复回测引擎 `backtest_service.py` 中 `sortino_ratio`、`calmar_ratio`、`monthly_returns` 三个未定义变量导致的 NameError 崩溃
- 修复 `AlpacaBroker` 的 `submit_order` 和 `cancel_order` 返回类型与 `BrokerAdapter` 基类不匹配（返回 `str`/`bool` 而非 `dict`），导致 `order_manager.py` 调用 `.get()` 时 `AttributeError`
- 重构 `PaperBroker` 从全局单例改为按用户实例化，消除跨用户状态泄漏
- 实现 API 请求限流中间件，使用 `RATE_LIMIT_PER_MINUTE` 和 `RATE_LIMIT_TRADE_PER_MINUTE` 配置项
- 实现回测并发控制（`MAX_CONCURRENT_BACKTESTS=3` 信号量）和超时控制（`BACKTEST_TIMEOUT_SECONDS=600`）
- 注册权益快照定时任务到 APScheduler
- 实现过期数据定时清理任务（`strategy_logs`、`alerts`、`market_data`、`notification_logs`）

## Capabilities

### New Capabilities
- `rate-limiting`: API 请求限流中间件，支持全局默认限制和交易接口单独限制
- `data-cleanup`: 过期数据定时清理，基于数据库 settings 表中配置的保留天数自动清理历史数据

### Modified Capabilities
<!-- 无现有 specs，无修改项 -->

## Impact

- **后端核心文件**: `backtest_service.py`、`brokers/alpaca.py`、`base.py`、`broker_factory.py`、`main.py`、`strategy_engine.py`
- **新增文件**: 限流中间件 `middleware/rate_limit.py`、数据清理服务 `services/cleanup_service.py`
- **API 行为变更**: 回测接口增加并发拒绝响应（429）；所有 API 接口增加限流头部
- **运行时行为变更**: 权益快照在每日 15:30 自动执行；过期数据在每日 03:00 自动清理
- **无数据库 schema 变更**: 所有修改均在应用层，无需 Alembic migration
