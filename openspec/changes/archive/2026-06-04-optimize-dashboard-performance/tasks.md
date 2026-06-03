## 1. 持仓价格缓存与估值逻辑

- [x] 1.1 在 `app/services/market_service.py` 中新增 `get_cached_prices(symbols: list[tuple[str, str]]) -> dict[str, Decimal]` 异步函数，批量并发获取价格并缓存到 Redis（key `price:{market}:{symbol}`，TTL 30s），缓存命中时直接返回
- [x] 1.2 `get_cached_prices` 对 AKShare（market=`a_stock`）做批量优化：当存在缓存 miss 的 A 股 symbol 时，一次调用 `stock_zh_a_spot_em()` 加载全量行情表，批量提取所有需要的 symbol 价格并分别写入 Redis，避免 N 次全量加载
- [x] 1.3 在 `app/services/account_service.py` 中提取 `calc_position_values(db, user_id) -> tuple[Decimal, list[dict]]`，使用 `get_cached_prices` 批量获取价格，返回总持仓市值和带 `current_price` 的持仓列表
- [x] 1.4 重构 `get_account_info()` 使用 `calc_position_values()`，消除内联的持仓估值循环
- [x] 1.5 重构 `save_equity_snapshot()` 使用 `calc_position_values()`，消除重复代码
- [x] 1.6 重构 `strategy_engine.py` 的 `_risk_check_job()` 使用 `calc_position_values()`（如适用）

## 2. 权益快照频率提升

- [x] 2.1 新增 alembic migration：`equity_snapshots` 表的 `date` 字段从 `String(10)` 改为 `DateTime` 类型，调整 unique constraint 为 `(user_id, timestamp)`；migration 中将已有数据转换为 `datetime`（旧 String 日期默认时间设为当天 15:30）
- [x] 2.2 更新 `EquitySnapshot` model 对应新的字段定义
- [x] 2.3 `strategy_engine.py` 中权益快照从 `CronTrigger(hour=15, minute=30)` 改为 `CronTrigger(minute=0)`（每小时整点触发，确保数据点时间一致）
- [x] 2.4 在交易成交事件处理流程中追加调用 `save_equity_snapshot()`，增加防抖：使用 Redis key `snapshot_lock:{user_id}` TTL 60s，距上次快照不足 60 秒时跳过

## 3. 后端接口修复

- [x] 3.1 `dashboard.py` 的 `get_overview` 接口使用 `DashboardOverview` schema 替代 `dict`，补充 `mode` 字段
- [x] 3.2 `dashboard.py` 的 `get_equity_curve` 接口，benchmark 改为使用 `account.initial_capital`（若无此字段则依次取系统参数 `paper_initial_capital` 或第一条 snapshot 的 `total_equity`）
- [x] 3.3 `dashboard.py` 的 `get_strategy_ranking` 接口移除 `status == "running"` 过滤，改为返回所有有回测结果的策略，并按 `total_return` 降序排序，限制前 10 条
- [x] 3.4 `GET /trade/positions` 接口（或 overview 内的持仓数据）返回 `current_price` 和 `market_value` 字段，供前端计算持仓分布
- [x] 3.5 `get_equity_curve` 接口在 range 为 ALL 或 1Y 时按天聚合（取每天最后一条快照），1D/1W 模式返回小时粒度数据，避免前端渲染过多数据点

## 4. 前端看板修复

- [x] 4.1 `DashboardView.vue` 的持仓分布图从 `qty * avg_price` 改为 `qty * current_price`（市值），数据来源使用 `current_price` 和 `market_value` 字段
- [x] 4.2 `DashboardView.vue` 接入 WebSocket：在组件 `onMounted` 时连接 WebSocket，监听 `trade_fill`、`order_update`、`risk_alert` 事件，调用 `queryClient.invalidateQueries()` 刷新对应数据
- [x] 4.3 WebSocket 断线重连策略：实现指数退避重连（1s → 2s → 4s → 最大 30s），重连成功后立即 invalidate 所有 dashboard query；token 过期时先刷新 token 再重连
- [x] 4.4 `DashboardView.vue` 在 `onUnmounted` 时清理 WebSocket 事件监听
- [x] 4.5 策略排名表增加"状态"列，展示每条策略的当前状态（running / stopped / error 等）
