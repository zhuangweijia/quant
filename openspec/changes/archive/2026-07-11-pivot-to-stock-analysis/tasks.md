## 1. 清理：移除交易域代码

- [x] 1.1 删除 `app/services/trade/` 整个目录（brokers/、order_manager.py、broker_factory.py、base.py）
- [x] 1.2 删除 `app/services/strategy_engine.py`、`risk_service.py`、`account_service.py`
- [x] 1.3 删除 `app/services/backtest_service.py`（后续以 model-validation 重建）
- [x] 1.4 删除旧模型文件：`models/account.py`、`order.py`、`position.py`、`equity_snapshot.py`、`risk_rule.py`、`risk_event.py`、`strategy.py`、`strategy_log.py`、`strategy_version.py`
- [x] 1.5 删除旧 API 路由：`api/v1/trade.py`、`strategy.py`、`strategy_logs.py`、`strategy_versions.py`、`risk.py`、`backtest.py`
- [x] 1.6 从 `api/v1/__init__.py` 和 `main.py` 中移除已删除路由的注册和 import
- [x] 1.7 从 `models/__init__.py` 中移除已删除模型的 import
- [x] 1.8 删除前端视图目录：`views/trade/`、`views/strategy/`、`views/risk/`、`views/backtest/`
- [x] 1.9 清理前端路由（`router/`）和导航菜单中已删除页面的入口
- [x] 1.10 从 `pyproject.toml` 移除 `ccxt`、`alpaca-py` 依赖，新增 `lightgbm`、`shap`、`scikit-learn`、`pandas-ta`
- [x] 1.11 清理 `config.py` 中 TRADING_MODE、broker 相关配置项
- [x] 1.12 运行 `lsp_diagnostics` 确认无残留引用错误

## 2. 数据库模型与迁移

- [x] 2.1 创建 `models/stock.py`：Stock 模型（symbol, name, industry, list_date, in_csi300, is_st, data_quality, last_synced_date）
- [x] 2.2 创建 `models/daily_bar.py`：DailyBar 模型（symbol, trade_date, open, high, low, close, volume, amount, turnover_rate）
- [x] 2.3 创建 `models/stock_factor.py`：StockFactor 模型（symbol, trade_date, factor_name, factor_value），或宽表设计（一行含全部因子列）
- [x] 2.4 创建 `models/prediction.py`：Prediction 模型（symbol, trade_date, score, rank, label, model_version, explanation JSONB, confidence）
- [x] 2.5 创建 `models/model_version.py`：ModelVersion 模型（version, trained_at, data_start, data_end, ic, val_accuracy, top_features JSONB, is_active, file_path）
- [x] 2.6 创建 `models/analysis_run.py`：AnalysisRun 模型（run_id, trigger_type, started_at, finished_at, stages JSONB, status, error）
- [x] 2.7 更新 `models/__init__.py` 注册新模型
- [x] 2.8 编写 Alembic 迁移脚本：drop 旧表（accounts, orders, positions, equity_snapshots, risk_rules, risk_events, strategies, strategy_logs, strategy_versions, backtest_results），create 新表
- [x] 2.9 执行迁移并验证表结构

## 3. 数据同步服务

- [x] 3.1 创建 `services/data_sync_service.py` 基础结构，定义 DataSyncService 类和同步状态追踪
- [x] 3.2 扩展 `market_service.py` 的 AKShareProvider：实现批量日K线历史下载（`stock_zh_a_hist`，前复权，指定日期范围）
- [x] 3.3 实现沪深300成分股列表同步：调用 AKShare 获取成分股代码、名称、行业，upsert 到 `stocks` 表，标记 `in_csi300`
- [x] 3.4 实现日K线全量同步：对沪深300每只股票拉取8年历史日K线，存入 `daily_bars` 表，支持进度记录和断点续传
- [x] 3.5 实现日K线增量同步：读取每只股票的 `last_synced_date`，仅拉取缺失日期的数据
- [x] 3.6 实现基本面数据同步：调用 AKShare 获取 PE/PB/ROE/营收增速/资产负债率/股息率，存为带时间戳快照
- [x] 3.7 实现北向资金持仓数据同步：获取沪深股通持股数据，计算 `northbound_holding_change`
- [x] 3.8 实现同步失败处理：单只股票失败不阻断整体同步，记录失败列表，下次优先重试
- [x] 3.9 实现数据完整性校验：检测连续交易日缺失，标记 `data_quality=warning`
- [x] 3.10 注册 APScheduler 定时任务：日K线+北向资金每日17:00同步，基本面每周日同步，成分股每月初同步
- [x] 3.11 创建首次全量拉取 CLI 脚本 `scripts/bootstrap_data.py`

## 4. 特征工程引擎

- [x] 4.1 创建 `services/feature_engine.py` 基础结构，定义 FeatureEngine 类和因子计算接口
- [x] 4.2 实现动量因子计算：5/10/20/60日收益率、相对沪深300超额收益（20日）、12月动量去掉最近1月
- [x] 4.3 实现估值因子计算：PE/PB/PS TTM、股息率的行业分位数（按申万一级行业分组计算百分位）
- [x] 4.4 实现质量因子计算：ROE TTM、毛利率、资产负债率、经营现金流/净利润比（含除零保护）
- [x] 4.5 实现成长因子计算：营收同比增速、净利润同比增速、营收环比增速
- [x] 4.6 实现量价因子计算：5日均换手率、20日波动率、20日量价相关系数、成交量比率
- [x] 4.7 实现技术指标因子计算：RSI(14)、MACD histogram、布林带位置（归一化0-1）、均线多头排列评分（0-4），使用 pandas-ta
- [x] 4.8 实现因子矩阵构建器：查询 `stock_factors` + `daily_bars` 组装为 DataFrame，行=symbol+date，列=因子名
- [x] 4.9 实现因子预处理：截面 Z-score 标准化（按日分组）、截面中位数填充 NaN、winsorize ±3σ
- [x] 4.10 实现特征计算结果写入 `stock_factors` 表

## 5. ML 选股模型

- [x] 5.1 创建 `services/ml_model.py` 基础结构，定义 MLModelService 类（train/predict/explain 方法）
- [x] 5.2 实现标签生成：从 `daily_bars` 计算每只股票未来5日相对沪深300超额收益，>+2%标为2，<-2%标为0，其余标为1
- [x] 5.3 实现训练集构建：walk-forward 滚动窗口（默认训练3年+验证6个月），因子矩阵 join 标签，对齐日期
- [x] 5.4 实现 LightGBM 训练：`objective=multiclass, num_class=3`，记录训练日志和特征重要性
- [x] 5.5 实现验证集评估：计算 IC（Spearman）、Top-decile 超额收益、验证集准确率
- [x] 5.6 实现模型存储：保存 `.txt` 到 `backend/models/`，记录 `model_versions` 表元数据
- [x] 5.7 实现每日预测：加载激活模型，输入最新日因子矩阵，输出 `score = P(跑赢) + 0.5*P(持平)`
- [x] 5.8 实现预测结果写入 `predictions` 表
- [x] 5.9 实现 SHAP 解释：`shap.TreeExplainer` 计算 SHAP 值，筛选 Top3 正向 + Top2 负向因子
- [x] 5.10 实现 SHAP 大白话翻译模板：为6大类因子编写自然语言模板（动量/估值/质量/成长/量价/技术），量化关键数值
- [x] 5.11 实现模型激活/停用 API 逻辑（含激活前回测门禁）
- [x] 5.12 实现模型信号监控：计算最近20日滚动IC，低于0.02标记 `confidence=low`

## 6. 排名服务

- [x] 6.1 创建 `services/ranking_service.py`，定义 generate_daily_ranking 方法
- [x] 6.2 实现排名生成：按评分降序排列，分配排名序号，按分位数分配标签（Top10%强推 / 10-40%关注 / 40-90%观望 / Bottom10%回避）
- [x] 6.3 实现排名变动追踪：查询前一交易日排名，计算变动值，新进入标记"NEW"
- [x] 6.4 更新 `predictions` 表的 `rank` 和 `label` 字段

## 7. 每日分析 Pipeline

- [x] 7.1 创建 `services/analysis_pipeline.py`，定义 AnalysisPipeline 类
- [x] 7.2 实现阶段编排：按序执行（数据同步 → 北向资金 → 特征计算 → 模型预测 → SHAP解释 → 排名生成）
- [x] 7.3 实现每阶段的开始/完成 WebSocket 事件推送（`analysis_progress`）
- [x] 7.4 实现完成事件推送（`ranking_ready`）
- [x] 7.5 实现 `analysis_runs` 表运行状态记录（stages JSONB、status、error）
- [x] 7.6 实现手动触发 API `POST /api/v1/analysis/trigger`，返回 run_id
- [x] 7.7 实现状态查询 API `GET /api/v1/analysis/status`
- [x] 7.8 实现阶段失败处理：停止后续阶段，标记 failed，推送通知
- [x] 7.9 实现非交易日检测：跳过执行并记录原因
- [x] 7.10 注册 APScheduler 定时任务（交易日17:00 CST）

## 8. API 端点

- [x] 8.1 创建 `api/v1/ranking.py`：`GET /api/v1/rankings`（支持 date、label 筛选、分页）
- [x] 8.2 创建 `api/v1/stock_detail.py`：`GET /api/v1/stocks/{symbol}/detail`（评分+SHAP+K线+基本面+北向）
- [x] 8.3 实现个股评分历史 API：`GET /api/v1/stocks/{symbol}/score-history?days=30`
- [x] 8.4 创建 `api/v1/model.py`：`GET /api/v1/model/versions`（版本列表）、`POST /api/v1/model/train`（触发训练）、`POST /api/v1/model/{version}/activate`（激活）
- [x] 8.5 在 `api/v1/__init__.py` 和 `main.py` 注册新路由
- [x] 8.6 创建对应的 Pydantic schemas（`schemas/ranking.py`、`schemas/stock_detail.py`、`schemas/model.py`、`schemas/analysis.py`）

## 9. 模型验证（回测）

- [x] 9.1 创建 `services/model_validation_service.py`，定义 quintile backtest 方法
- [x] 9.2 实现分组回测：按历史排名分5组，计算每组等权日收益序列
- [x] 9.3 实现关键指标计算：年化收益、最大回撤、夏普比率、IC均值、IC胜率、Top-Bottom多空收益
- [x] 9.4 实现回测 API `POST /api/v1/model/backtest`（指定时间范围和模型版本）
- [x] 9.5 实现回测结果可视化数据（分组累计收益曲线、IC时间序列、月度收益热力图）
- [x] 9.6 实现模型激活前门禁：IC < 0.02 或未跑过回测时拒绝激活
- [x] 9.7 实现多版本回测对比 API

## 10. 前端 — 排名表与个股详情

- [x] 10.1 创建 `views/ranking/RankingView.vue`：每日排名表（排名/代码/名称/评分/标签/较昨日变动），支持标签筛选和分页
- [x] 10.2 实现排名表样式：强推绿色高亮、回避红色标记、大幅变动（>50名）特殊标记、NEW 标签
- [x] 10.3 创建 `views/stock-detail/StockDetailView.vue`：评分卡片 + SHAP 因素拆解 + K线图 + 基本面 + 北向资金
- [x] 10.4 实现 SHAP 解释展示组件：Top3正向 + Top2负向，大白话文字 + 因子值 + SHAP贡献条形图
- [x] 10.5 实现 K 线图组件（复用 ECharts，展示60日OHLCV）
- [x] 10.6 实现因子市场分位数可视化（条形图展示各因子在全市场的百分位）
- [x] 10.7 实现评分历史趋势图（折线图：个股评分 vs 沪深300）
- [x] 10.8 创建前端 API 封装（`api/ranking.ts`、`api/stock.ts`、`api/model.ts`、`api/analysis.ts`）
- [x] 10.9 更新路由注册和导航菜单（移除旧入口，新增 排名表 / 个股详情 / 模型管理）
- [x] 10.10 添加 Pipeline 状态指示器组件（进度条 + 当前阶段）

## 11. 前端 — Dashboard 改造与模型管理

- [x] 11.1 改造 `views/dashboard/DashboardView.vue`：从 P&L 看板 → 市场概览 + 今日Top10 + Pipeline状态
- [x] 11.2 实现 Top10 强推股票卡片列表（评分 + 标签 + 点击跳转详情）
- [x] 11.3 实现市场概览面板（沪深300当日涨跌、强推/回避数量、平均评分分布）
- [x] 11.4 创建 `views/model/ModelView.vue`：模型版本列表 + 训练触发 + 激活 + 回测对比
- [x] 11.5 实现回测结果可视化页面（分组收益曲线 + IC序列 + 指标表格）
- [x] 11.6 更新 WebSocket 订阅：`analysis_progress` → 更新进度条，`ranking_ready` → 刷新排名缓存，`data_sync_alert` → 警告横幅
- [x] 11.7 改造 `views/market/MarketView.vue`：简化为选股浏览器（搜索 + K线图 + 基本面，移除实时行情和下单）

## 12. 初始化、引导与部署

- [x] 12.1 编写首次数据引导流程：运行 `bootstrap_data.py` 拉取沪深300历史数据，显示进度
- [x] 12.2 首次模型训练并验证 IC 达标后激活
- [x] 12.3 更新 `README.md`：移除交易/加密货币/美股相关描述，更新为A股AI选股分析平台
- [x] 12.4 更新 `docker-compose.yml` 和 Dockerfile（移除不需要的服务，调整环境变量）
- [x] 12.5 更新 `.env.example`：移除 TRADING_MODE/broker配置，新增 ANALYSIS_TIME/STOCK_UNIVERSE 等
- [x] 12.6 端到端验证：触发 Pipeline → 数据同步 → 特征计算 → 预测 → 排名 → 前端展示完整链路
- [x] 12.7 确认 `lsp_diagnostics` 在所有修改的文件上无错误
