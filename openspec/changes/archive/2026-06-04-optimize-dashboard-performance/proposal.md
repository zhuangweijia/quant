## Why

看板是用户进入系统的第一个页面，但当前存在严重性能问题和数据准确性问题：`overview` 接口对每个持仓串行调用外部 API 获取实时价格（10 个持仓 = 10 次 HTTP 请求），响应时间可达数秒；权益快照每天只在 15:30 生成一次，盘中权益曲线完全平坦；日盈亏依赖快照计算，盘中不准确；持仓分布图展示的是成本而非市值；看板没有使用已有的 WebSocket 推送，完全靠 HTTP 轮询，数据不会自动更新。

## What Changes

- 将持仓实时价格获取从串行外部 API 调用改为批量并发 + Redis 缓存（TTL 30s），AKShare 做批量优化（一次全量加载、批量提取）
- 提取持仓估值逻辑为共享函数，消除 `get_account_info()`、`save_equity_snapshot()`、`_risk_check_job()` 三处重复代码
- 权益快照从每天一次改为每小时整点生成（`CronTrigger(minute=0)`），并在交易成交时追加生成（带防抖机制，60s 内不重复）
- 修复权益曲线 benchmark 为真实基准线（初始资金）而非水平线
- 持仓分布图从 `qty * avg_price`（成本）改为 `qty * current_price`（市值）
- 前端看板接入 WebSocket（含指数退避重连策略），订单成交、风控告警时自动刷新对应查询
- overview 接口返回类型从 `dict` 改为使用已有的 `DashboardOverview` Pydantic schema
- 策略排名扩展为包含所有有回测结果的策略（不限于 running 状态）
- equity-curve ALL/1Y 模式后端按天聚合返回，1D/1W 返回小时粒度

## Capabilities

### New Capabilities
- `dashboard-realtime`: 看板 WebSocket 实时推送，订单成交、持仓变动、风控告警时自动刷新看板数据

### Modified Capabilities

## Impact

- **后端**: `account_service.py`（持仓估值提取 + 批量并发）、`dashboard.py`（schema、策略排名）、`strategy_engine.py`（快照频率）
- **后端新增**: Redis 缓存层用于持仓实时价格
- **前端**: `DashboardView.vue`（WebSocket 接入、持仓分布修正）、`useDashboardQuery.ts`（实时刷新）
- **API 兼容性**: `GET /dashboard/overview` 返回结构不变，但增加 `mode` 字段（已存在但 schema 未声明）；`GET /dashboard/strategy-ranking` 返回范围扩大（非 breaking）
- **定时任务**: 权益快照从 `CronTrigger(hour=15, minute=30)` 改为 `CronTrigger(minute=0)`（每小时整点）
- **数据库 migration**: `equity_snapshots.date` 从 `String(10)` 改为 `DateTime`；需处理已有数据类型转换
