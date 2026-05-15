# QuantPlatform 详细需求文档

> 版本: 2.0 | 更新日期: 2026-05-15
> 定位: 多市场量化交易平台 — 支持 A股、美股、加密货币的模拟盘/实盘交易

---

## 目录

- [一、平台现状评估](#一平台现状评估)
- [二、整体架构规划](#二整体架构规划)
- [三、模块详细需求](#三模块详细需求)
  - [1. 认证与用户管理](#1-认证与用户管理)
  - [2. 看板 (Dashboard)](#2-看板-dashboard)
  - [3. 行情中心](#3-行情中心)
  - [4. 策略管理](#4-策略管理)
  - [5. 回测引擎](#5-回测引擎)
  - [6. 实盘/模拟交易](#6-实盘模拟交易)
  - [7. 风控系统](#7-风控系统)
  - [8. 系统设置](#8-系统设置)
  - [9. 通知系统](#9-通知系统)
  - [10. WebSocket 实时通信](#10-websocket-实时通信)
- [四、非功能性需求](#四非功能性需求)
- [五、优先级与里程碑](#五优先级与里程碑)

---

## 一、平台现状评估

| 模块 | 完成度 | 关键缺口 |
|------|--------|----------|
| 认证系统 | 85% | 无注册页面、无 Token 自动刷新、无验证码 |
| 看板 | 50% | 权益曲线用假数据、日盈亏始终为 0、无实时更新 |
| 行情中心 | 60% | 仅 Mock 数据 + A股 AKShare、无实时推送、自选不持久化 |
| 策略管理 | 40% | 策略引擎缺失（仅改状态）、代码编辑器为纯文本框、无策略模板 |
| 回测引擎 | 30% | 始终跑硬编码 SMA 交叉、不加载用户策略代码、无图表展示结果 |
| 交易系统 | 60% | 仅 PaperBroker、无真实券商适配器、无订单超时处理 |
| 风控系统 | 55% | 止损/止盈未实现、日亏损/日交易次数始终为 0、无自动强平 |
| 系统设置 | 20% | 所有保存操作为空操作（NO-OP）、无持久化表 |
| 通知系统 | 5% | 端点存在但全部硬编码、邮件/Webhook 测试始终失败 |
| WebSocket | 0% | 目录存在但为空、前端零实现 |

**总体完成度: ~40%**

---

## 二、整体架构规划

### 2.1 后端技术栈

```
FastAPI + Uvicorn
├── SQLAlchemy 2.0 (async) + Alembic
├── Redis (事件总线 + 缓存 + 实时推送)
├── APScheduler (策略调度、定时任务)
├── WebSocket (FastAPI 原生)
└── 结构化日志 (structlog)
```

### 2.2 前端技术栈

```
Vue 3 + TypeScript + Vite
├── Element Plus (UI 组件库)
├── ECharts (图表)
├── Pinia (状态管理)
├── Monaco Editor (代码编辑器)
└── WebSocket Client (实时数据)
```

### 2.3 数据流架构

```
行情数据源 (AKShare/Alpaca/Binance)
       │
       ▼
  MarketDataProvider ──→ Redis Pub/Sub ──→ WebSocket ──→ 前端
       │                                        │
       ▼                                        ▼
  Strategy Engine ──→ OrderManager ──→ BrokerAdapter
       │                    │
       ▼                    ▼
  RiskEvaluator       事件总线 ──→ 通知系统
```

---

## 三、模块详细需求

---

### 1. 认证与用户管理

#### 1.1 现有功能

- 用户名 + 密码登录
- JWT RS256 双 Token（access 30min + refresh 7day）
- 登录失败 5 次锁定 15 分钟
- 第一个注册用户自动成为管理员
- 角色: admin / trader / viewer

#### 1.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| AUTH-01 | 注册页面 | P0 | 前端增加注册表单，支持用户名/密码/确认密码，管理员可关闭开放注册 |
| AUTH-02 | Token 自动刷新 | P0 | Access Token 过期前 5 分钟自动调用 refresh 接口，无需用户重新登录 |
| AUTH-03 | 图形验证码 | P1 | 登录页增加图形验证码（登录失败 3 次后强制），防止暴力破解 |
| AUTH-04 | 用户管理（管理员） | P1 | 管理员可查看用户列表、禁用/启用用户、重置密码、修改角色 |
| AUTH-05 | 操作审计日志 | P2 | 记录关键操作（登录/登出/策略启停/下单/修改设置），提供查询界面 |
| AUTH-06 | 会话管理 | P2 | 用户可查看活跃会话、强制下线其他设备；管理员可强制下线任意用户 |

#### 1.3 数据模型变更

```
新增表: audit_logs
  - id, user_id, action, target_type, target_id, detail, ip, user_agent, created_at

新增表: user_sessions
  - id, user_id, refresh_token_jti, device_info, ip, expires_at, created_at
```

---

### 2. 看板 (Dashboard)

#### 2.1 现有功能

- 4 个统计卡片（总资产、日盈亏、总盈亏、运行中策略数）
- 权益曲线图（Mock 数据）
- 持仓分布饼图
- 策略表现表 + 最近订单表

#### 2.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| DASH-01 | 真实权益曲线 | P0 | 从 account + order 表聚合每日收盘权益，按天/小时粒度展示 |
| DASH-02 | 真实日盈亏 | P0 | 计算当日已实现盈亏 + 未实现盈亏变动，替代硬编码的 0 |
| DASH-03 | 实时数据刷新 | P0 | 通过 WebSocket 推送持仓变动、订单状态变化，卡片数据自动更新 |
| DASH-04 | 收益概览时间选择 | P1 | 支持查看今日 / 近7日 / 近30日 / 近1年 / 全部的收益数据 |
| DASH-05 | 策略表现增强 | P1 | 增加策略运行时长、交易次数、胜率、盈亏比等核心指标 |
| DASH-06 | 快捷操作面板 | P2 | 看板上提供快捷入口: 一键启停策略、快速下单、查看最新告警 |
| DASH-07 | 大屏模式 | P3 | 提供全屏看板展示，适合大屏监控场景 |

#### 2.3 数据模型变更

```
新增表: equity_snapshots
  - id, user_id, date, total_equity, cash, position_value, daily_pnl, created_at
  - 每日收盘自动快照，或每小时快照（取决于交易模式）
```

---

### 3. 行情中心

#### 3.1 现有功能

- K 线图（ECharts 蜡烛图 + 成量）
- 品种搜索（Mock 20 个标的）
- 自选股（内存态，刷新丢失）
- 实时报价（Polling 拉取）
- 支持时间周期: 1m/5m/15m/30m/1h/4h/1d/1w

#### 3.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| MKT-01 | A股完整数据 | P0 | AKShare 接入沪深股票实时行情、历史 K 线、分时数据 |
| MKT-02 | 美股数据 (Alpaca) | P1 | Alpaca Market Data API 接入美股实时/历史数据 |
| MKT-03 | 加密货币数据 (Binance) | P1 | Binance WebSocket API 接入实时行情 |
| MKT-04 | 实时行情推送 | P0 | 后端通过 WebSocket 推送 tick/bar 数据到前端，替代轮询 |
| MKT-05 | 自选股持久化 | P0 | 新增 user_watchlist 表，自选股保存到数据库，跨设备同步 |
| MKT-06 | 技术指标叠加 | P1 | K 线图支持叠加 MA/EMA/BOLL/MACD/KDJ/RSI 等常用技术指标 |
| MKT-07 | 多图联动 | P2 | 支持同时查看多个标的，或主图+副图（如 K 线 + 成交量 + MACD） |
| MKT-08 | 品种详情页 | P2 | 点击标的进入详情页，展示基本面信息、财务数据、相关新闻 |
| MKT-09 | 行情数据缓存 | P1 | Redis 缓存热门标的数据，减少外部 API 调用 |
| MKT-10 | 数据订阅管理 | P2 | 用户按需订阅品种，只推送订阅的数据，减少带宽和计算量 |

#### 3.3 数据模型变更

```
新增表: user_watchlist
  - id, user_id, symbol, market, sort_order, created_at
  - UNIQUE(user_id, symbol, market)

market_data 表增加索引优化:
  - 复合索引 (symbol, market, timeframe, timestamp) — 已存在
  - 定期清理策略，按 data_retention_days 配置清理历史数据
```

---

### 4. 策略管理

#### 4.1 现有功能

- 策略 CRUD（创建/编辑/删除/软删除）
- 策略状态管理 (draft → running → stopped)
- 策略代码存储（纯文本）
- 最多 50 个策略、最多 10 个同时运行
- 默认 Python 模板（BaseStrategy 子类）

#### 4.2 关键缺口

> **这是平台最核心的缺口**: `BaseStrategy` 已定义但从未被加载执行。启动/停止策略仅修改数据库状态，无实际代码运行。

#### 4.3 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| STR-01 | 策略执行引擎 | P0 | 加载用户策略代码，在沙箱环境中实例化 BaseStrategy 并运行。支持 on_init/on_bar/on_tick/on_order/on_trade/on_stop 生命周期 |
| STR-02 | 策略调度器 | P0 | APScheduler 集成，按策略配置的周期（on_bar 的 timeframe）定时拉取行情并触发策略回调 |
| STR-03 | 代码编辑器升级 | P0 | 替换 textarea 为 Monaco Editor，提供 Python 语法高亮、自动补全、错误提示 |
| STR-04 | 策略模板库 | P1 | 提供预置策略模板: 双均线交叉、布林带突破、RSI 超买超卖、网格交易、动量策略等 |
| STR-05 | 策略参数表单化 | P1 | 策略参数定义从 JSON 文本改为结构化表单（支持 int/float/bool/enum/select 类型），前端自动渲染参数表单 |
| STR-06 | 策略日志 | P0 | 策略运行时的 log() 输出持久化，提供实时查看和搜索界面 |
| STR-07 | 策略运行监控 | P1 | 策略详情页展示: 运行状态、最近触发时间、触发次数、关联订单、关联持仓、运行日志 |
| STR-08 | 策略安全沙箱 | P1 | 限制策略代码的 import 和系统调用，防止恶意代码（如禁止 os、subprocess、socket 等） |
| STR-09 | 策略版本管理 | P2 | 每次编辑保存产生新版本，可回滚到历史版本，查看 diff |
| STR-10 | 策略导入/导出 | P2 | 支持导出策略为 .py 文件，支持从 .py 文件导入 |

#### 4.4 策略执行引擎设计

```
StrategyEngine
  │
  ├── StrategyLoader
  │     └── 从 Strategy.code 加载 Python 代码
  │     └── 在受限命名空间中执行，提取 BaseStrategy 子类
  │     └── 安全检查: 禁止危险 import
  │
  ├── StrategyRuntime (每个运行中的策略一个实例)
  │     └── 持有 strategy 实例、关联的 strategy_id、user_id
  │     └── 绑定 broker_adapter (PaperBroker / 真实券商)
  │     └── 绑定 market_data_provider (获取历史/实时数据)
  │     └── 绑定 order_manager (下单)
  │
  └── StrategyScheduler
        └── 根据 timeframe 注册定时任务
        └── on_bar: 到达新 K 线时触发
        └── on_tick: 收到新 tick 时触发（通过事件总线）
```

#### 4.5 数据模型变更

```
新增表: strategy_logs
  - id, strategy_id, user_id, level, message, created_at
  - INDEX(strategy_id, created_at)

新增表: strategy_versions
  - id, strategy_id, version, code, params, change_note, created_at
  - INDEX(strategy_id, version)
```

---

### 5. 回测引擎

#### 5.1 现有功能

- 回测运行接口（异步后台任务）
- 结果列表 + 详情查看 + 删除
- 计算指标: 总收益率、年化收益、夏普比率、索提诺比率、最大回撤、卡尔玛比率、胜率、盈亏比
- 存储权益曲线、回撤曲线、交易记录、月度收益
- **关键问题: 始终运行硬编码的 SMA 交叉，不加载用户策略**

#### 5.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| BT-01 | 加载用户策略代码 | P0 | 从 Strategy.code 加载 BaseStrategy 子类，用用户策略替代硬编码 SMA |
| BT-02 | 回测结果可视化 | P0 | 前端展示: 权益曲线图、回撤曲线图、月度收益热力图、交易标记在 K 线图上 |
| BT-03 | 回测进度推送 | P1 | 通过 WebSocket 推送回测进度百分比，前端显示进度条 |
| BT-04 | 并发回测限制 | P1 | 实现 MAX_CONCURRENT_BACKTESTS=3 的限制，排队机制 |
| BT-05 | 回测参数优化 | P2 | 支持参数扫描（网格搜索），对多组参数运行回测，找出最优参数组合 |
| BT-06 | 基准对比 | P1 | 回测结果与买入持有基准对比，展示超额收益 |
| BT-07 | 交易明细表 | P0 | 回测详情中展示每笔交易的: 入场时间/价格、出场时间/价格、盈亏、持仓时间 |
| BT-08 | 回测报告导出 | P2 | 支持导出回测报告为 PDF/Excel |
| BT-09 | 平均持仓时间计算 | P1 | 实现 avg_holding_period 的真实计算（当前始终为 0） |
| BT-10 | 滑点和手续费模拟 | P1 | 回测参数增加滑点百分比、手续费率设置，模拟更真实的交易成本 |

#### 5.3 回测引擎设计

```
BacktestEngine
  │
  ├── 加载策略代码 → 实例化 BaseStrategy
  │
  ├── 数据准备
  │     └── 从 MarketDataProvider 获取历史 K 线数据
  │     └── 按时间顺序遍历
  │
  ├── 模拟交易
  │     └── 内置 BacktestBroker (模拟撮合)
  │     └── 支持市价单/限价单/止损单
  │     └── 计算手续费、滑点
  │
  ├── 指标计算
  │     └── 收益率、夏普、索提诺、最大回撤、卡尔玛、胜率、盈亏比
  │     └── 权益曲线、回撤曲线、月度收益、交易统计
  │
  └── 结果存储 → BacktestResult 表
```

---

### 6. 实盘/模拟交易

#### 6.1 现有功能

- PaperBroker（内存模拟券商）: 市价单/限价单/止损单撮合、滑点、手续费
- 订单管理: 下单、撤单、平仓、冻结/解冻持仓
- A 股 100 股整手限制
- 持仓查询、订单历史查询
- 账户信息（总资产 = 现金 + 持仓市值）

#### 6.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| TRD-01 | Alpaca 券商适配器 | P1 | 对接 Alpaca Trading API，支持美股 paper/live 交易 |
| TRD-02 | Binance 券商适配器 | P1 | 对接 Binance API，支持加密货币现货交易 |
| TRD-03 | 订单超时处理 | P0 | 实现 ORDER_TIMEOUT_SECONDS=30，超时未成交自动撤单 |
| TRD-04 | 交易时间校验 | P0 | 下单前检查市场是否开放（A 股 9:30-15:00、美股对应美东时间等），拒绝非交易时段订单 |
| TRD-05 | 持仓盈亏实时计算 | P0 | 未实现盈亏 = (当前价 - 成本价) × 数量，通过行情数据实时计算 |
| TRD-06 | 订单状态流转完善 | P0 | 实现完整的订单生命周期: pending → submitted → partial_filled → filled / cancelled / rejected |
| TRD-07 | 交易确认机制 | P1 | 实盘模式下大额交易需二次确认（输入交易密码） |
| TRD-08 | 持仓明细增强 | P1 | 展示: 持仓成本、当前市值、浮动盈亏（金额+百分比）、今仓/昨仓、可用数量 |
| TRD-09 | 分页支持 | P1 | 订单列表、持仓列表支持分页查询和筛选（按时间、标的、状态） |
| TRD-10 | 交易手续费统计 | P2 | 统计各策略/整体的手续费支出 |

#### 6.3 券商适配器架构

```
BrokerAdapter (ABC)
  ├── submit_order()
  ├── cancel_order()
  ├── get_order_status()
  ├── get_positions()
  ├── get_account()
  └── health_check()

已实现:
  └── PaperBroker — 内存模拟

待实现:
  ├── AlpacaBroker — 美股 (HTTP REST + WebSocket)
  └── BinanceBroker — 加密货币 (REST + WebSocket)

工厂模式:
  get_broker(market, mode) → 返回对应的 BrokerAdapter
    - mode=paper → PaperBroker (所有市场)
    - mode=live + market=us_stock → AlpacaBroker
    - mode=live + market=crypto → BinanceBroker
    - mode=live + market=a_stock → 暂不支持，提示用户
```

---

### 7. 风控系统

#### 7.1 现有功能

- 6 种风控规则: 单标的持仓限额、总持仓比例、日亏损限制、日交易次数限制、黑名单、单笔金额限制
- 规则作用域: 全局 / 策略级
- 规则优先级排序
- 下单前风控检查
- 告警创建与通知
- 告警标记已读 / 全部已读

#### 7.2 关键缺口

- 止损/止盈规则定义了但未实现评估器
- 日亏损和日交易次数始终为 0，相关规则永远不会触发
- 无自动强平机制

#### 7.3 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| RSK-01 | 止损规则实现 | P0 | 支持固定价格止损、百分比止损、移动止损（Trailing Stop） |
| RSK-02 | 止盈规则实现 | P0 | 支持固定价格止盈、百分比止盈 |
| RSK-03 | 日亏损/日交易次数真实计算 | P0 | 从 orders 表聚合当日已实现亏损和交易次数，替代硬编码 0 |
| RSK-04 | 自动强平 | P0 | 当触发严重风控规则（如总亏损超过阈值）时自动平仓 |
| RSK-05 | 风控规则触发历史 | P1 | 记录每次风控规则的触发详情（时间、规则、订单、原因），提供查询界面 |
| RSK-06 | 风控仪表盘 | P1 | 展示当前风控状态概览: 各规则触发次数、最近告警、风险评分 |
| RSK-07 | 实时风控监控 | P1 | 通过 WebSocket 实时推送风控告警到前端，Header 显示未读告警数角标 |
| RSK-08 | 策略级风控回调 | P1 | 风控触发时可配置: 仅告警 / 自动暂停策略 / 自动平仓 |
| RSK-09 | 规则参数表单化 | P2 | 规则参数从 JSON 文本改为根据 rule_type 动态渲染的结构化表单 |
| RSK-10 | 最大回撤规则 | P2 | 新增最大回撤监控规则，当策略回撤超过阈值时告警/暂停 |

#### 7.4 止损/止盈执行机制

```
PriceMonitor (定时任务)
  │
  ├── 每次行情更新时检查所有持仓
  │
  ├── 止损检查
  │     └── 当前价 ≤ 止损价 → 自动卖出
  │     └── 移动止损: 当前价 ≤ (最高价 × (1 - 回撤百分比)) → 自动卖出
  │
  ├── 止盈检查
  │     └── 当前价 ≥ 止盈价 → 自动卖出
  │
  └── 自动强平检查
        └── 总权益 ≤ 初始资金 × (1 - 强平阈值) → 全部平仓
```

---

### 8. 系统设置

#### 8.1 现有功能

- 券商配置展示（硬编码，保存为空操作）
- 交易模式切换（paper/live）
- 通知配置（保存为空操作）
- 系统参数展示（硬编码默认值，保存为空操作）
- 个人资料 + 修改密码

#### 8.2 关键缺口

> **所有保存操作都是 NO-OP**: broker save、notification save、system params save 全部直接返回，没有任何持久化逻辑。需要新增 settings 表。

#### 8.3 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| SET-01 | 设置持久化 | P0 | 新增 settings 表，所有设置项保存到数据库，支持按 user_id 隔离 |
| SET-02 | 券商 API Key 加密存储 | P0 | 使用已有的 Encryption 工具对 API Key/Secret 加密后存储 |
| SET-03 | 券商连接状态实时检测 | P1 | 设置页展示券商真实连接状态（健康检查），而非硬编码 |
| SET-04 | 系统参数分类管理 | P1 | 参数按类别分组: 策略限制、超时设置、资金与费率、数据保留 |
| SET-05 | 参数变更审计 | P2 | 记录参数变更历史，管理员可查看谁在何时修改了什么参数 |
| SET-06 | 主题设置 | P3 | 支持亮色/暗色主题切换，偏好保存到用户设置 |
| SET-07 | 多语言支持 | P3 | i18n 框架集成，支持中文/英文切换 |

#### 8.4 数据模型变更

```
新增表: settings
  - id, user_id, category, key, value (TEXT/JSON), encrypted (BOOL), created_at, updated_at
  - UNIQUE(user_id, category, key)
  - user_id=NULL 表示全局设置

示例数据:
  - (NULL, 'system', 'max_strategies_per_user', '50', false)
  - (user_id, 'broker', 'alpaca_api_key', 'encrypted:...', true)
  - (user_id, 'notification', 'email_config', '{"host":"smtp.xxx"}', false)
```

---

### 9. 通知系统

#### 9.1 现有功能

- 告警模型 (alerts 表) + CRUD API
- 通知配置端点（全部 NO-OP）
- 邮件/Webhook 测试端点（始终返回失败）

#### 9.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| NOTI-01 | 站内通知中心 | P0 | 前端 Header 显示未读通知角标，点击展开通知面板，支持标记已读 |
| NOTI-02 | 邮件通知 | P1 | SMTP 集成，支持发送: 风控告警、策略异常、每日交易报告 |
| NOTI-03 | Webhook 通知 | P1 | 支持推送到企业微信/钉钉/飞书/自定义 Webhook |
| NOTI-04 | 通知规则配置 | P1 | 用户可配置哪些事件触发哪些通知渠道: 风控告警 → 邮件+Webhook |
| NOTI-05 | 通知模板 | P2 | 可自定义通知内容模板，支持变量插值（如 {strategy_name}、{pnl}） |
| NOTI-06 | 每日报告 | P2 | 每日收盘后自动生成交易日报，推送至配置的通知渠道 |
| NOTI-07 | 通知发送记录 | P2 | 记录所有已发送通知的状态、时间、内容，支持查询 |

#### 9.3 通知系统架构

```
NotificationDispatcher
  │
  ├── 接收事件 (通过 Redis 事件总线)
  │     └── risk:alert → 风控告警
  │     └── strategy:log (level=ERROR) → 策略异常
  │     └── trade:fill → 成交通知
  │     └── daily:report → 日报触发
  │
  ├── 匹配通知规则
  │     └── 查询用户的 NotificationRule 配置
  │
  └── 分发通知
        ├── 站内 → 写入 alerts 表 → WebSocket 推送前端
        ├── 邮件 → SMTP 发送
        └── Webhook → HTTP POST
```

---

### 10. WebSocket 实时通信

#### 10.1 现有功能

- 后端 `app/ws/` 目录存在但为空
- 前端 Vite 配置代理 `/ws` 路径
- 前端零实现

#### 10.2 新增需求

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| WS-01 | WebSocket 服务端 | P0 | FastAPI WebSocket 端点，JWT 鉴权，按用户隔离连接 |
| WS-02 | 行情数据推送 | P0 | 实时推送订阅标的的 tick/bar 数据 |
| WS-03 | 订单状态推送 | P0 | 订单状态变化实时推送（提交、部分成交、全部成交、撤销、拒绝） |
| WS-04 | 持仓变动推送 | P0 | 持仓数量/市值变化实时推送 |
| WS-05 | 风控告警推送 | P0 | 风控规则触发时实时推送告警 |
| WS-06 | 策略日志推送 | P1 | 策略运行日志实时推送到前端 |
| WS-07 | 回测进度推送 | P1 | 回测运行进度百分比推送 |
| WS-08 | 心跳与重连 | P0 | 客户端定期 ping，服务端 pong；断线自动重连，指数退避 |
| WS-09 | 连接管理 | P1 | 单用户最多 5 个连接，超限踢出最早的；服务端维护连接映射表 |
| WS-10 | 前端 WebSocket 封装 | P0 | 统一的 WebSocket 客户端类，自动鉴权、重连、消息分发 |

#### 10.3 WebSocket 消息协议

```json
// 通用消息格式
{
  "type": "market.tick | market.bar | trade.order | trade.position | risk.alert | strategy.log | backtest.progress",
  "data": { ... },
  "timestamp": 1715769600000
}

// 订阅/取消订阅
{ "action": "subscribe", "channels": ["market.tick:AAPL", "trade.order"] }
{ "action": "unsubscribe", "channels": ["market.tick:AAPL"] }

// 心跳
{ "action": "ping" }  →  { "action": "pong" }
```

---

## 四、非功能性需求

### 4.1 性能

| 需求 | 目标 |
|------|------|
| API 平均响应时间 | < 200ms（非计算密集型接口） |
| WebSocket 消息延迟 | < 100ms |
| 支持 100 个策略同时运行 | 内存 < 2GB |
| 行情数据缓存命中率 | > 80% |
| 前端首屏加载 | < 3s |

### 4.2 安全

| 需求 | 说明 |
|------|------|
| API Key 加密存储 | Fernet 对称加密，密钥通过环境变量注入 |
| 策略沙箱隔离 | 禁止 os/subprocess/socket/file 等危险模块 |
| SQL 注入防护 | SQLAlchemy ORM 参数化查询（已满足） |
| XSS 防护 | Vue 模板自动转义（已满足） |
| CSRF 防护 | JWT Token 方案天然防 CSRF（已满足） |
| 限流 | 实现配置中定义的 rate limit（60/min 通用，10/min 交易） |
| HTTPS | 生产环境强制 HTTPS |

### 4.3 可靠性

| 需求 | 说明 |
|------|------|
| 数据库迁移 | Alembic 管理所有 schema 变更 |
| 优雅关闭 | 策略引擎在收到终止信号时完成当前 K 线处理后再退出 |
| 数据备份 | PostgreSQL 每日自动备份，保留 30 天 |
| 错误恢复 | 策略异常不崩溃平台，捕获异常 → 标记策略为 error → 通知用户 |
| 日志持久化 | 结构化日志输出，支持 ELK/Loki 等日志系统采集 |

### 4.4 可测试性

| 需求 | 说明 |
|------|------|
| 后端单元测试 | 覆盖率 > 70%，pytest + pytest-asyncio |
| 后端集成测试 | 覆盖所有 API 端点 |
| 前端组件测试 | Vitest + @vue/test-utils |
| 前端 E2E 测试 | Playwright 覆盖核心用户流程 |

### 4.5 前端体验优化

| 需求 | 说明 |
|------|------|
| 分页组件 | 所有列表页支持分页（策略列表、订单列表、告警列表、回测结果） |
| 加载状态 | NProgress 路由切换进度条 + 骨架屏 |
| 响应式布局 | 适配 1280px+ 桌面端，1280px 以下可横向滚动 |
| 错误边界 | 全局异常捕获，友好错误页面 |
| Token 刷新 | Access Token 过期前自动刷新，用户无感知 |

---

## 五、优先级与里程碑

### P0 — 核心功能（必须完成，平台可用）

> 预计工期: 3-4 周

| 序号 | 需求 | 模块 |
|------|------|------|
| 1 | 策略执行引擎 (STR-01) | 策略管理 |
| 2 | 策略调度器 (STR-02) | 策略管理 |
| 3 | 策略日志 (STR-06) | 策略管理 |
| 4 | 回测加载用户策略 (BT-01) | 回测引擎 |
| 5 | 回测结果可视化 (BT-02) | 回测引擎 |
| 6 | 回测交易明细 (BT-07) | 回测引擎 |
| 7 | 真实权益曲线 (DASH-01) | 看板 |
| 8 | 真实日盈亏 (DASH-02) | 看板 |
| 9 | 实时数据刷新 (DASH-03) | 看板 |
| 10 | 止损规则 (RSK-01) | 风控 |
| 11 | 止盈规则 (RSK-02) | 风控 |
| 12 | 日亏损/日交易次数真实计算 (RSK-03) | 风控 |
| 13 | 自动强平 (RSK-04) | 风控 |
| 14 | 设置持久化 (SET-01) | 系统设置 |
| 15 | API Key 加密存储 (SET-02) | 系统设置 |
| 16 | WebSocket 服务端 + 前端封装 (WS-01/10) | 实时通信 |
| 17 | 行情/订单/持仓/告警推送 (WS-02~05) | 实时通信 |
| 18 | 站内通知中心 (NOTI-01) | 通知系统 |
| 19 | 订单超时处理 (TRD-03) | 交易 |
| 20 | 交易时间校验 (TRD-04) | 交易 |
| 21 | 持仓盈亏实时计算 (TRD-05) | 交易 |
| 22 | 注册页面 (AUTH-01) | 认证 |
| 23 | Token 自动刷新 (AUTH-02) | 认证 |
| 24 | 自选股持久化 (MKT-05) | 行情 |
| 25 | A股完整数据 (MKT-01) | 行情 |
| 26 | 代码编辑器升级 (STR-03) | 策略管理 |

### P1 — 重要功能（体验提升）

> 预计工期: 2-3 周

| 序号 | 需求 | 模块 |
|------|------|------|
| 1 | 图形验证码 (AUTH-03) | 认证 |
| 2 | 用户管理 (AUTH-04) | 认证 |
| 3 | 收益时间选择 (DASH-04) | 看板 |
| 4 | 策略表现增强 (DASH-05) | 看板 |
| 5 | 美股数据 Alpaca (MKT-02) | 行情 |
| 6 | 加密货币 Binance (MKT-03) | 行情 |
| 7 | 技术指标叠加 (MKT-06) | 行情 |
| 8 | 行情数据缓存 (MKT-09) | 行情 |
| 9 | 策略模板库 (STR-04) | 策略管理 |
| 10 | 策略参数表单化 (STR-05) | 策略管理 |
| 11 | 策略运行监控 (STR-07) | 策略管理 |
| 12 | 策略安全沙箱 (STR-08) | 策略管理 |
| 13 | 回测进度推送 (BT-03) | 回测 |
| 14 | 并发回测限制 (BT-04) | 回测 |
| 15 | 基准对比 (BT-06) | 回测 |
| 16 | 平均持仓时间 (BT-09) | 回测 |
| 17 | 滑点手续费模拟 (BT-10) | 回测 |
| 18 | Alpaca 券商适配器 (TRD-01) | 交易 |
| 19 | Binance 券商适配器 (TRD-02) | 交易 |
| 20 | 交易确认机制 (TRD-07) | 交易 |
| 21 | 持仓明细增强 (TRD-08) | 交易 |
| 22 | 分页支持 (TRD-09) | 交易 |
| 23 | 风控触发历史 (RSK-05) | 风控 |
| 24 | 风控仪表盘 (RSK-06) | 风控 |
| 25 | 实时风控推送 (RSK-07) | 风控 |
| 26 | 策略级风控回调 (RSK-08) | 风控 |
| 27 | 券商连接检测 (SET-03) | 设置 |
| 28 | 系统参数分类 (SET-04) | 设置 |
| 29 | 邮件通知 (NOTI-02) | 通知 |
| 30 | Webhook 通知 (NOTI-03) | 通知 |
| 31 | 通知规则配置 (NOTI-04) | 通知 |
| 32 | 策略日志推送 (WS-06) | 实时通信 |
| 33 | 回测进度推送 (WS-07) | 实时通信 |
| 34 | 连接管理 (WS-09) | 实时通信 |

### P2 — 增强功能（锦上添花）

> 预计工期: 2 周

| 序号 | 需求 | 模块 |
|------|------|------|
| 1 | 操作审计日志 (AUTH-05) | 认证 |
| 2 | 会话管理 (AUTH-06) | 认证 |
| 3 | 快捷操作面板 (DASH-06) | 看板 |
| 4 | 多图联动 (MKT-07) | 行情 |
| 5 | 品种详情页 (MKT-08) | 行情 |
| 6 | 数据订阅管理 (MKT-10) | 行情 |
| 7 | 策略版本管理 (STR-09) | 策略管理 |
| 8 | 策略导入/导出 (STR-10) | 策略管理 |
| 9 | 参数优化 (BT-05) | 回测 |
| 10 | 回测报告导出 (BT-08) | 回测 |
| 11 | 交易手续费统计 (TRD-10) | 交易 |
| 12 | 规则参数表单化 (RSK-09) | 风控 |
| 13 | 最大回撤规则 (RSK-10) | 风控 |
| 14 | 参数变更审计 (SET-05) | 设置 |
| 15 | 通知模板 (NOTI-05) | 通知 |
| 16 | 每日报告 (NOTI-06) | 通知 |
| 17 | 通知发送记录 (NOTI-07) | 通知 |

### P3 — 未来功能

| 需求 | 模块 |
|------|------|
| 大屏模式 (DASH-07) | 看板 |
| 主题设置 (SET-06) | 设置 |
| 多语言支持 (SET-07) | 设置 |

---

## 附录 A: 新增数据模型汇总

```sql
-- 权益快照
CREATE TABLE equity_snapshots (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    date       DATE NOT NULL,
    total_equity DECIMAL(20,4),
    cash       DECIMAL(20,4),
    position_value DECIMAL(20,4),
    daily_pnl  DECIMAL(20,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- 自选股
CREATE TABLE user_watchlist (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    symbol     TEXT NOT NULL,
    market     TEXT NOT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol, market)
);

-- 策略日志
CREATE TABLE strategy_logs (
    id          TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL REFERENCES strategies(id),
    user_id     TEXT NOT NULL REFERENCES users(id),
    level       TEXT NOT NULL DEFAULT 'INFO',
    message     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_strategy_logs_sid ON strategy_logs(strategy_id, created_at);

-- 策略版本
CREATE TABLE strategy_versions (
    id          TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL REFERENCES strategies(id),
    version     INT NOT NULL,
    code        TEXT NOT NULL,
    params      JSONB,
    change_note TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(strategy_id, version)
);

-- 系统设置
CREATE TABLE settings (
    id         TEXT PRIMARY KEY,
    user_id    TEXT REFERENCES users(id),  -- NULL = 全局
    category   TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT,
    encrypted  BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, category, key)
);

-- 审计日志
CREATE TABLE audit_logs (
    id           TEXT PRIMARY KEY,
    user_id      TEXT REFERENCES users(id),
    action       TEXT NOT NULL,
    target_type  TEXT,
    target_id    TEXT,
    detail       JSONB,
    ip           TEXT,
    user_agent   TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 用户会话
CREATE TABLE user_sessions (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    refresh_token_jti TEXT NOT NULL UNIQUE,
    device_info       TEXT,
    ip                TEXT,
    expires_at        TIMESTAMPTZ NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 风控触发记录
CREATE TABLE risk_events (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    strategy_id TEXT REFERENCES strategies(id),
    rule_id     TEXT NOT NULL REFERENCES risk_rules(id),
    order_id    TEXT REFERENCES orders(id),
    rule_type   TEXT NOT NULL,
    result      TEXT NOT NULL,  -- block / warn / auto_close
    detail      JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 通知发送记录
CREATE TABLE notification_logs (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    channel     TEXT NOT NULL,  -- email / webhook / in_app
    event_type  TEXT NOT NULL,
    title       TEXT,
    content     TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending / sent / failed
    error       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 附录 B: API 端点变更汇总

### 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 前端注册（已有后端，缺前端页面） |
| GET | `/api/v1/admin/users` | 管理员: 用户列表 |
| PUT | `/api/v1/admin/users/{id}/status` | 管理员: 禁用/启用用户 |
| PUT | `/api/v1/admin/users/{id}/role` | 管理员: 修改角色 |
| POST | `/api/v1/admin/users/{id}/reset-password` | 管理员: 重置密码 |
| GET | `/api/v1/admin/audit-logs` | 管理员: 审计日志查询 |
| GET | `/api/v1/strategies/{id}/logs` | 策略运行日志 |
| GET | `/api/v1/strategies/{id}/versions` | 策略版本列表 |
| GET | `/api/v1/strategies/{id}/versions/{ver}` | 策略版本详情 |
| POST | `/api/v1/strategies/{id}/rollback` | 回滚到指定版本 |
| GET | `/api/v1/market/watchlist` | 获取自选股列表 |
| POST | `/api/v1/market/watchlist` | 添加自选股 |
| DELETE | `/api/v1/market/watchlist/{id}` | 删除自选股 |
| GET | `/api/v1/risk/events` | 风控触发历史 |
| GET | `/api/v1/notifications/logs` | 通知发送记录 |
| WS | `/ws` | WebSocket 连接 |

### 行为变更

| 端点 | 变更 |
|------|------|
| `POST /api/v1/backtest/run` | 加载用户策略代码执行，不再硬编码 SMA |
| `GET /api/v1/dashboard/equity-curve` | 返回真实权益数据 |
| `GET /api/v1/dashboard/overview` | 日盈亏使用真实计算值 |
| `GET /api/v1/trade/account` | 包含真实未实现盈亏 |
| `PUT /api/v1/settings/brokers/{name}` | 持久化 + 加密 API Key |
| `PUT /api/v1/settings/notifications` | 持久化通知配置 |
| `PUT /api/v1/settings/params` | 持久化系统参数 |
| `POST /api/v1/trade/order` | 增加交易时间校验 + 订单超时机制 |
