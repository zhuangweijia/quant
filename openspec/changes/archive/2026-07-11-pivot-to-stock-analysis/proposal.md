## Why

当前系统是一个多市场量化交易平台，交易执行链路（broker 适配、订单状态机、风控强平、实时撮合）占据了最大的工程复杂度，却是单人自用场景下最不需要的部分。将系统转型为 A 股 AI 选股分析平台，砍掉交易域，聚焦"用 ML 模型发现选股规律并每日输出排名"，可将系统复杂度降低一个量级，同时交付真正的核心价值——每日选股排名表。

## What Changes

- **BREAKING**: 移除交易执行系统——PaperBroker / Alpaca / Binance broker 适配器、订单管理、持仓管理、Account 余额链路
- **BREAKING**: 移除策略引擎——用户代码 exec 沙箱、策略定时执行、策略日志
- **BREAKING**: 移除实盘风控系统——止损/止盈规则、自动强平、持仓限额
- **BREAKING**: 移除加密货币和美股市场支持，仅保留 A 股
- **BREAKING**: 移除前端 trade / strategy / risk / backtest 页面
- 新增：A 股历史数据增量同步服务（沪深 300 起步，AKShare 数据源）
- 新增：特征工程引擎——自动计算动量、估值、质量、成长、量价、资金流、技术指标等 6 大类因子
- 新增：ML 选股模型——LightGBM 跨截面收益预测，训练 + 预测 + SHAP 解释
- 新增：每日分析 Pipeline——收盘后自动跑：数据同步 → 特征计算 → 模型预测 → 排名生成
- 新增：每日排名 API 与前端排名表页面——全市场评分排名、分档（强推 / 观望 / 回避）
- 新增：个股钻取页面——评分明细、SHAP 因素拆解（大白话解释）、K 线图、基本面
- 新增：模型验证能力——复用回测骨架，验证"按排名选股能否跑赢沪深 300"
- 改造：Dashboard 从"P&L 看板"转为"市场概览 + 今日 Top 10"
- 改造：自选股从"交易标的观察"转为"选股观察池"，叠加模型评分
- 保留：认证系统、系统设置（精简）、WebSocket 基建、Docker 部署、Redis 缓存、PostgreSQL、审计日志、数据清理

## Capabilities

### New Capabilities

- `data-sync`: A 股历史数据与基本面数据的增量同步服务，支持沪深 300 股票池的日 K 线、基本面快照、北向资金持仓的采集、存储与断点续传
- `feature-engineering`: 特征工程引擎，自动计算动量 / 估值 / 质量 / 成长 / 量价 / 资金流 / 技术指标 6 大类因子，输出每只股票每日的因子快照
- `ml-stock-model`: ML 选股模型，使用 LightGBM 进行跨截面收益预测，包含模型训练、预测、SHAP 解释、版本管理
- `daily-analysis-pipeline`: 每日分析编排管道，收盘后按序执行数据同步 → 特征计算 → 模型预测 → 排名生成，支持手动触发和定时调度
- `stock-ranking`: 每日股票排名与分档，输出全市场评分排名表（强推 / 观望 / 回避），支持历史排名回溯
- `stock-detail`: 个股钻取能力，展示评分明细、SHAP 因素拆解（大白话）、K 线图、基本面数据
- `model-validation`: 模型验证能力，复用回测骨架验证"按排名分组选股"的历史表现，输出分组收益、IC、夏普等指标

### Modified Capabilities

- `dashboard-realtime`: Dashboard 订阅的 WebSocket 事件从 `order_update` / `trade_fill` / `risk_alert` 改为 `ranking_ready` / `analysis_progress`，刷新的数据从 P&L / 持仓改为市场概览 / 今日 Top 10

## Impact

- **后端代码**：删除 `app/services/trade/`、`app/services/strategy_engine.py`、`app/services/risk_service.py`、`app/services/account_service.py`、`app/services/backtest_service.py`（改造后重建为 model-validation）；删除 `app/models/` 下的 account / order / position / equity_snapshot / risk_* / strategy* 模型；删除 `app/api/v1/` 下 trade / strategy* / risk / backtest 路由
- **新增后端模块**：`data_sync_service.py`、`feature_engine.py`、`ml_model.py`、`ranking_service.py`、`analysis_pipeline.py`；新增 stock / daily_bar / stock_factor / prediction 模型
- **前端**：删除 trade / strategy / risk / backtest 视图目录，新增 ranking / stock-detail / model 视图目录，改造 dashboard 和 market 视图
- **数据库**：需要 Alembic 迁移删除旧表、创建新表；新表包含 stock、daily_bar、stock_factor、prediction、model_version 等
- **依赖**：新增 lightgbm、shap、scikit-learn、pandas-ta（或 talib）依赖；移除 ccxt、alpaca-py 依赖
- **配置**：移除 TRADING_MODE、broker 相关配置；新增 ANALYSIS_TIME、STOCK_UNIVERSE、MODEL_PARAMS 等配置项
- **数据迁移**：首次部署需执行沪深 300 历史数据全量拉取（预计小时级）
