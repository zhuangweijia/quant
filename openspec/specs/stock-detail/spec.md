## ADDED Requirements

### Requirement: 个股详情综合视图

系统 SHALL 提供个股钻取页面，综合展示该股票的评分明细、SHAP 因素拆解、K 线图、基本面数据和资金流向。

#### Scenario: 查询个股详情
- **WHEN** 前端通过 `GET /api/v1/stocks/{symbol}/detail` 查询个股详情
- **THEN** 系统 SHALL 返回：股票基本信息（代码、名称、行业、市值）、最新评分与排名、评分分位数、标签
- **AND** SHALL 返回 SHAP 解释（Top 3 正向因素、Top 2 负向因素，每项含因子名、SHAP值、大白话描述、原始数值）
- **AND** SHALL 返回最近 60 个交易日的日K线数据（OHLCV）
- **AND** SHALL 返回最新基本面指标（PE/PB/ROE/营收增速/资产负债率）
- **AND** SHALL 返回最近 20 日北向资金持仓变化趋势

### Requirement: 个股评分历史趋势

系统 SHALL 提供个股评分的历史趋势查询，展示该股票近期评分变化。

#### Scenario: 查询个股评分历史
- **WHEN** 前端通过 `GET /api/v1/stocks/{symbol}/score-history?days=30` 查询评分历史
- **THEN** 系统 SHALL 返回该股票最近 30 个交易日的评分序列（日期 + 评分 + 排名 + 标签）
- **AND** SHALL 返回同期沪深300指数收益率用于对比
- **AND** 评分无数据的交易日 SHALL 填充为 NULL

### Requirement: 因子横向对比

系统 SHALL 在个股详情中提供该股票各项因子在当日全市场的百分位排名，帮助用户理解该股票在市场中的相对位置。

#### Scenario: 展示因子市场分位数
- **WHEN** 个股详情页面渲染因子数据
- **THEN** 每个因子 SHALL 展示该股票的原始值 + 全市场百分位（0-100%）
- **AND** 百分位 SHALL 按因子方向校准（如 PE 越低越好，则 PE 低百分位标为"优"）
- **AND** SHALL 以可视化条形图展示各因子的百分位位置
