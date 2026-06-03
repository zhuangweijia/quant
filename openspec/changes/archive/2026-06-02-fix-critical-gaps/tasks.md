## 1. P0 致命 Bug 修复

- [x] 1.1 修复 `backtest_service.py` 回测引擎 NameError：在 `_execute_backtest` 函数中补全 `sortino_ratio`（下行标准差计算）、`calmar_ratio`（年化收益/最大回撤）、`monthly_returns`（从 equity_curve 按年月分组计算收益率）三个变量的计算逻辑
- [x] 1.2 修复 `brokers/alpaca.py` AlpacaBroker 返回类型：将 `_submit_order_sync` 返回值从 `resp.id`(str) 改为 `{"broker_order_id": str, "status": str, "filled_qty": Decimal, "filled_price": Decimal|None, "commission": Decimal}` 的 dict；将 `cancel_order` 返回值从 `bool` 改为 `{"status": "cancelled"}` 或 `{"status": "error", "reason": str}` 的 dict
- [x] 1.3 修复 `brokers/alpaca.py` AlpacaBroker 增加 stop order 支持：在 `_submit_order_sync` 中添加 `StopOrderRequest` 分支

## 2. PaperBroker 状态隔离

- [x] 2.1 修改 `base.py` 中 `get_paper_broker()` 函数，移除全局单例，改为每次返回新实例
- [x] 2.2 修改 `broker_factory.py` 的 `get_broker_for_user`，paper 模式下按 `paper:{user_id}` 缓存 PaperBroker 实例到 `_broker_cache`

## 3. 回测并发与超时控制

- [x] 3.1 在 `backtest_service.py` 模块级添加 `asyncio.Semaphore(3)` 信号量
- [x] 3.2 修改 `run_backtest` 函数：在 `_execute_backtest` 调用前检查信号量是否可用，不可用时拒绝并返回错误
- [x] 3.3 修改 `_execute_backtest` 函数：用 `async with semaphore` 包裹主逻辑，用 `asyncio.timeout(600)` 包裹执行体，超时后标记 result 为 failed

## 4. 权益快照定时任务

- [x] 4.1 在 `strategy_engine.py` 的 `start()` 方法中注册 APScheduler cron job：每日 15:30 执行 `save_equity_snapshot`，遍历所有活跃用户

## 5. API 限流中间件

- [x] 5.1 创建 `middleware/rate_limit.py`：实现 `RateLimitMiddleware(BaseHTTPMiddleware)`，基于内存字典的滑动窗口计数器
- [x] 5.2 实现限流规则：默认 60/分钟（按 IP 或 user_id）、`/api/v1/trade/` 路径 10/分钟、`/api/v1/backtest/run` 路径 3/分钟
- [x] 5.3 实现豁免路径：`/health`、`/api/docs`、`/api/redoc` 不受限流
- [x] 5.4 实现响应头：每个请求响应添加 `X-RateLimit-Limit`、`X-RateLimit-Remaining`、`X-RateLimit-Reset`
- [x] 5.5 在 `main.py` 中注册 `RateLimitMiddleware`，读取 `config.py` 中的 `RATE_LIMIT_PER_MINUTE` 和 `RATE_LIMIT_TRADE_PER_MINUTE`

## 6. 过期数据定时清理

- [x] 6.1 创建 `services/cleanup_service.py`：实现 `run_cleanup()` 函数，从 settings 表读取保留天数配置
- [x] 6.2 实现分批删除逻辑：每批 5000 条，循环删除直到无过期记录
- [x] 6.3 覆盖清理范围：`strategy_logs`（log_retention_days）、`alerts`（alert_retention_days）、`notification_logs`（log_retention_days）、`market_data`（data_retention_days）
- [x] 6.4 实现清理日志：记录各表删除条数和总耗时
- [x] 6.5 在 `strategy_engine.py` 的 `start()` 方法中注册 APScheduler cron job：每日 03:00 执行 `run_cleanup`
