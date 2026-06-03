## Context

QuantPlatform 的看板页面是用户核心入口，当前包含 4 个数据卡片（总资产、日盈亏、总盈亏、运行策略）、权益曲线图、持仓分布饼图、策略排名表、最近订单表。数据通过 6 个独立 HTTP 接口获取。

核心瓶颈在 `get_account_info()`：对每个持仓串行调用 `get_latest_price()` 获取实时价格来计算总权益和持仓市值。这个逻辑在三处重复出现（overview 接口、权益快照定时任务、风控检查定时任务）。

后端已有完整的 WebSocket 基础设施（`ws_manager`），支持频道订阅、按用户推送，且在 `main.py` 中已对接事件总线的订单/持仓/风控事件。但前端看板未接入 WebSocket，完全依赖 HTTP 轮询。

权益快照当前通过 APScheduler 的 `CronTrigger(hour=15, minute=30)` 每天生成一次，盘中无数据。

## Goals / Non-Goals

**Goals:**
- overview 接口响应时间从秒级降到 200ms 以内（典型场景：5 个持仓）
- 权益曲线在盘中能看到当日变化（至少每小时一个数据点）
- 看板数据在订单成交、风控告警时自动更新，无需手动刷新
- 持仓分布图展示真实市值而非成本
- 消除持仓估值逻辑的三处代码重复

**Non-Goals:**
- 不重新设计看板 UI 布局
- 不引入新的外部依赖（使用已有的 Redis 和 ccxt/akshare）
- 不改变 WebSocket 协议格式（复用现有的 `type` + `data` 结构）
- 不做行情数据的全量缓存（只缓存看板需要的最新价）

## Decisions

### D1: 持仓价格缓存 — Redis String + TTL 30s

**选择**：在 Redis 中为每个 symbol 缓存最新价格，key 为 `price:{market}:{symbol}`，TTL 30 秒。

**备选方案**：
- A) 每次 overview 请求都实时调外部 API — 当前行为，N 个持仓串行调用太慢
- B) 数据库缓存 — 写入频率高，增加 DB 负担
- C) 内存缓存（Python dict）— 多 worker/多进程不共享

**理由**：Redis 已部署，天然支持 TTL，多 worker 共享。30s TTL 在实时性和外部 API 调用频率之间取得平衡。overview 请求最多调一次外部 API 批量刷新，其余时间命中缓存。

**批量并发策略**：使用 `asyncio.gather()` 并发获取所有持仓的价格，而非串行。即使缓存未命中，也是 N 个并发请求而非 N 个串行请求。

**AKShare 特殊处理**：`AKShareProvider.get_latest_price()` 每次调用 `stock_zh_a_spot_em()` 会加载全量 A 股行情表，逐个调用等于 N 次全量加载。`get_cached_prices` 应对 AKShare 做批量优化：一次调用 `stock_zh_a_spot_em()` 加载整张表，批量提取所有需要的 symbol 价格，然后分别写入 Redis。仅当存在缓存 miss 的 A 股 symbol 时触发全量加载。

### D2: 持仓估值逻辑提取 — 共享 async 函数

**选择**：在 `account_service.py` 中提取 `calc_position_values(db, user_id) -> (position_value, positions_with_price)` 函数，返回总持仓市值和带当前价格的持仓列表。`get_account_info()`、`save_equity_snapshot()`、`_risk_check_job()` 均调用此函数。

**备选方案**：
- A) 在 market_service 层加缓存 — 改动范围更大，且不同场景的缓存策略可能不同
- B) 在 broker_factory 层处理 — 只适用于有 broker 的场景

**理由**：最小改动范围，消除重复的同时保持现有架构不变。

### D3: 权益快照频率 — 从每天一次改为每小时 + 交易触发

**选择**：
- APScheduler 从 `CronTrigger(hour=15, minute=30)` 改为 `CronTrigger(minute=0)`（每小时整点触发），确保数据点时间一致
- 在交易成交回调中追加调用 `save_equity_snapshot()`，增加防抖机制：距上次快照不足 60 秒时跳过（使用 Redis key `snapshot_lock:{user_id}` TTL 60s）

**备选方案**：
- A) 每 5 分钟快照 — 数据更密但 DB 写入压力大
- B) 只在交易触发 — 如果没有交易，整天没有数据点
- C) `IntervalTrigger(hours=1)` — 从启动时刻计时，每次重启后快照时间漂移，数据点不对齐

**理由**：`CronTrigger(minute=0)` 保证每小时整点触发，数据时间轴一致，对权益曲线展示更友好。交易触发加防抖避免批量订单场景（策略一次下 5 单）短时间内生成多条冗余快照。一天约 24 条记录 + 少量交易触发记录，DB 负担可接受。需修改 `EquitySnapshot` 的 `date` 字段（String(10)）为 `DateTime` 类型，调整 unique constraint。

### D4: WebSocket 看板刷新 — 前端监听事件 + invalidateQueries

**选择**：前端在 `DashboardView.vue` 中通过 WebSocket 监听 `order_update`、`trade_fill`、`risk_alert` 事件，收到后调用 vue-query 的 `queryClient.invalidateQueries()` 刷新对应数据。

**备选方案**：
- A) 后端推送完整数据 — 需要新的消息格式，后端压力大
- B) 定时轮询 — 简单但不实时，浪费请求

**理由**：复用已有 WebSocket 基础设施，前端只需加事件监听 + invalidate，改动最小。vue-query 的 invalidate 会自动去重和按需请求。

### D5: 权益曲线 benchmark — 改为账户初始资金常量线

**选择**：`equity-curve` 接口返回的 `benchmark` 字段统一使用 `account.initial_capital`。若 `Account` model 无此字段，从系统参数 `paper_initial_capital`（纸盘）或第一条 `EquitySnapshot.total_equity`（实盘）中获取。

**理由**：当前 `benchmark` 是第一个 snapshot 的 `total_equity`（和 equity 起点相同），画出来是一条和权益曲线重合的水平线。改为初始资金后，可以直观看到"初始投入 vs 当前权益"的对比。

**数据来源优先级**：`account.initial_capital` → `get_system_params()["paper_initial_capital"]` → 第一条 snapshot 的 `total_equity`（兜底）。

### D6: 持仓分布图 — 传递 current_price 而非用 avg_price

**选择**：`GET /dashboard/overview` 接口在返回持仓数据时附带 `current_price`，前端用它计算市值。或者直接在已有的 `GET /trade/positions` 接口返回 `market_value` 字段。

**理由**：最小改动。后端在 `calc_position_values` 中已经获取了实时价格，可以直接附加到持仓数据中。

## Risks / Trade-offs

- **[Redis 缓存价格可能过期]** → 30s TTL 意味着价格最多滞后 30 秒。对看板概览场景足够，不影响交易下单（下单时仍实时获取）。可在 UI 上标注"价格延迟约 30 秒"。
- **[AKShare 全量加载]** → 即使缓存 miss 只有一只 A 股，也需要加载全量行情表。通过"一次全量加载、批量写入缓存"可将代价摊薄为单次调用。若所有 A 股 symbol 均命中 Redis 缓存则零开销。
- **[每小时快照增加 DB 写入]** → 每用户每天约 24 条，远小于风控检查每分钟一次的频率。`equity_snapshots` 表当前 `date` 字段为 `String(10)`，改为 hourly 需将字段类型变更为 `DateTime`。migration 中需处理已有 String 数据的类型转换（旧数据默认时间设为当天 15:30）。
- **[交易触发快照防抖]** → 批量订单场景短时间内多次触发 `save_equity_snapshot()`，通过 Redis 锁（TTL 60s）实现防抖，避免冗余写入。
- **[WebSocket 断线重连]** → 前端需实现指数退避重连策略（1s → 2s → 4s → 最大 30s），重连成功后立即 invalidate 所有 dashboard query 以补齐断线期间遗漏的更新。Token 过期时需先刷新 token 再重连。
- **[策略排名范围扩大]** → 包含非 running 状态的策略可能让列表变长。前端已有空状态处理，非 breaking 变更。
- **[equity-curve ALL 模式数据量]** → 改为每小时一条后，一年约 8760 条/用户，前端图表渲染大量数据点可能卡顿。ALL/1Y 模式下应在后端做按天聚合（取每天最后一条快照），只有 1D/1W 模式返回小时粒度数据。
- **[overview 200ms 目标]** → Redis 缓存只解决了价格获取问题，overview 仍有策略数、订单数、告警数等多个 DB 查询。实际目标应为 P95 < 500ms。如需进一步优化，可对策略数/告警数做 1 分钟短期缓存。
