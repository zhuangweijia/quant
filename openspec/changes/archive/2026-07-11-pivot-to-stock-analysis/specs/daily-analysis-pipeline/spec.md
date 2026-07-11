## ADDED Requirements

### Requirement: 每日分析 Pipeline 编排

系统 SHALL 提供一个编排服务（AnalysisPipeline），按固定顺序执行每日分析的各个阶段：数据同步 → 特征计算 → 模型预测 → 排名生成。

#### Scenario: 定时触发每日Pipeline
- **WHEN** 交易日收盘后（默认 17:00 CST），APScheduler 定时触发 AnalysisPipeline
- **THEN** Pipeline SHALL 按序执行以下阶段：1) 日K线增量同步 2) 北向资金同步 3) 特征计算 4) 模型预测 5) SHAP解释 6) 排名生成
- **AND** 每个阶段开始和完成时 SHALL 通过 WebSocket 推送进度事件 `analysis_progress`
- **AND** 全部阶段完成后 SHALL 推送 `ranking_ready` 事件

#### Scenario: 手动触发Pipeline
- **WHEN** 用户通过 API `POST /api/v1/analysis/trigger` 手动触发 Pipeline
- **THEN** 系统 SHALL 执行完整 Pipeline，与定时触发行为一致
- **AND** 手动触发 SHALL 返回一个 `run_id` 用于追踪执行进度

#### Scenario: Pipeline阶段失败处理
- **WHEN** Pipeline 中某个阶段执行失败
- **THEN** 系统 SHALL 停止后续阶段，标记本次运行为 `failed`
- **AND** SHALL 记录失败阶段和错误信息到 `analysis_runs` 表
- **AND** SHALL 通过 WebSocket 推送失败通知
- **AND** 数据同步阶段的单只股票失败 SHALL 不阻断整体 Pipeline（只在特征计算阶段校验数据完整性）

### Requirement: Pipeline 执行状态追踪

系统 SHALL 记录每次 Pipeline 运行的完整状态，支持前端查询执行进度和历史。

#### Scenario: 查询Pipeline运行状态
- **WHEN** 前端通过 `GET /api/v1/analysis/status` 查询当前或最近一次运行
- **THEN** 系统 SHALL 返回：运行ID、触发方式（manual/scheduled）、各阶段状态（pending/running/done/failed）、开始时间、结束时间、错误信息
- **AND** WebSocket 事件 `analysis_progress` SHALL 实时推送阶段状态变更

#### Scenario: 非交易日不执行Pipeline
- **WHEN** 定时触发时间到达但当日非 A 股交易日（周末 / 节假日）
- **THEN** 系统 SHALL 跳过本次执行
- **AND** SHALL 记录跳过原因为 `non_trading_day`
