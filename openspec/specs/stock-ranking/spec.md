## ADDED Requirements

### Requirement: 每日股票评分排名

系统 SHALL 基于模型预测评分对沪深300全部成分股进行排名，并按分档输出：Top 10% 标记为"强推"，Top 10%-40% 标记为"关注"，Bottom 40%-90% 标记为"观望"，Bottom 10% 标记为"回避"。

#### Scenario: 生成每日排名表
- **WHEN** Pipeline 执行到排名生成阶段
- **THEN** 系统 SHALL 读取当日全部成分股的预测评分
- **AND** 按评分降序排列，分配排名序号（1-300）
- **AND** 按分位数分配标签：Top 10% → "强推"，Top 10%-40% → "关注"，Bottom 40%-90% → "观望"，Bottom 10% → "回避"
- **AND** 排名结果 SHALL 存入 `predictions` 表的 `rank` 和 `label` 字段

### Requirement: 排名 API 查询

系统 SHALL 提供 API 查询每日排名表，支持按标签筛选、分页、和历史日期回溯。

#### Scenario: 查询当日排名表
- **WHEN** 前端通过 `GET /api/v1/rankings?date=today` 查询当日排名
- **THEN** 系统 SHALL 返回当日全部成分股的排名列表，每条记录包含：排名序号、股票代码、股票名称、评分、标签、较前一日排名变化
- **AND** SHALL 支持按标签筛选（`?label=强推`）和分页（`?page=1&size=30`）

#### Scenario: 查询历史日期排名
- **WHEN** 前端通过 `GET /api/v1/rankings?date=2026-07-01` 查询历史排名
- **THEN** 系统 SHALL 返回该交易日的排名表
- **AND** 若该日期无排名数据（非交易日 / Pipeline未执行），SHALL 返回 404 并提示"该日期无排名数据"

### Requirement: 排名变化追踪

系统 SHALL 计算每只股票的排名较前一交易日的变动，并在排名表中展示。

#### Scenario: 排名变化计算
- **WHEN** 排名生成时
- **THEN** 系统 SHALL 查询前一交易日的排名数据
- **AND** 计算排名变动 = 前日排名 - 今日排名（正值表示上升）
- **AND** 新进入排名的股票（此前不在成分股）SHALL 标记为"NEW"

#### Scenario: 展示排名大幅变动
- **WHEN** 前端展示排名表
- **THEN** 排名上升超过 50 名的股票 SHALL 以高亮样式标记
- **AND** 排名下降超过 50 名的股票 SHALL 以不同颜色标记
