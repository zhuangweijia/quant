## ADDED Requirements

### Requirement: 动量因子计算

系统 SHALL 为每只股票在每个交易日计算动量类因子，包括：5日收益率、10日收益率、20日收益率、60日收益率、相对沪深300超额收益（20日）、12月动量去掉最近1月。

#### Scenario: 动量因子批量计算
- **WHEN** 分析 Pipeline 执行到特征计算阶段
- **THEN** 系统 SHALL 从 `daily_bars` 表读取每只成分股的历史日K线
- **AND** 基于收盘价计算上述动量因子
- **AND** 结果 SHALL 存储到 `stock_factors` 表，包含 `trade_date`、`symbol`、因子名、因子值

#### Scenario: 历史数据不足时的降级处理
- **WHEN** 某只股票上市不满 60 个交易日（如新股）
- **THEN** 系统 SHALL 跳过需要 60 日窗口的因子计算，该因子值设为 NULL
- **AND** 其他不依赖长窗口的因子 SHALL 正常计算
- **AND** 系统 SHALL 在因子元数据中标记该股票的数据覆盖率为 `partial`

### Requirement: 估值因子计算

系统 SHALL 为每只股票计算估值类因子：PE TTM、PB、PS TTM、股息率，并计算各因子在所属行业内的分位数排名。

#### Scenario: 估值因子计算与行业分位数
- **WHEN** 特征计算阶段执行估值因子计算
- **THEN** 系统 SHALL 从基本面快照读取最新 PE/PB/PS/股息率
- **AND** 按申万一级行业分类，计算该股票各项估值指标的行业内百分位排名（0-1）
- **AND** 行业分位数 SHALL 作为独立因子存储

### Requirement: 质量与成长因子计算

系统 SHALL 计算质量因子（ROE TTM、毛利率、资产负债率、经营现金流/净利润比）和成长因子（营收同比增速、净利润同比增速、营收环比增速）。

#### Scenario: 财务指标因子计算
- **WHEN** 特征计算阶段执行质量/成长因子计算
- **THEN** 系统 SHALL 从基本面快照读取最新财务指标
- **AND** 计算 ROE TTM = 净利润TTM / 股东权益TTM
- **AND** 所有比率指标 SHALL 除零保护，分母为零时因子值为 NULL

### Requirement: 量价因子计算

系统 SHALL 从日K线数据计算量价因子：5日均换手率、20日波动率（日收益率标准差）、20日量价相关系数、成交量比率（当日量 / 20日均量）。

#### Scenario: 量价因子计算
- **WHEN** 特征计算阶段执行量价因子计算
- **THEN** 系统 SHALL 基于日K线的收盘价和成交量计算上述因子
- **AND** 20日波动率 SHALL 使用最近20个交易日的日收益率标准差（年化可选）

### Requirement: 技术指标因子计算

系统 SHALL 计算技术指标因子：RSI(14)、MACD信号（histogram正负 + 柱高）、布林带位置（价格在带中的位置 0-1）、均线多头排列评分。

#### Scenario: 技术指标因子计算
- **WHEN** 特征计算阶段执行技术指标计算
- **THEN** 系统 SHALL 使用 pandas-ta 或等价库计算 RSI(14)、MACD(12,26,9)、Bollinger(20,2)、MA(5/10/20/60)
- **AND** 布林带位置 SHALL 归一化到 [0, 1] 区间
- **AND** 均线多头排列评分 SHALL 为 0-4 的整数（MA5>MA10>MA20>MA60 的满足层数）

### Requirement: 因子矩阵输出

系统 SHALL 将所有因子组织为二维矩阵（行=股票×日期，列=因子），用于模型训练和预测。

#### Scenario: 生成训练用因子矩阵
- **WHEN** 模型训练阶段请求因子矩阵
- **THEN** 系统 SHALL 查询 `stock_factors` 表，构建 DataFrame（index=symbol+date, columns=因子名）
- **AND** SHALL 对每列因子做截面标准化（Cross-sectional Z-score，按日分组），消除量纲差异
- **AND** NaN 值 SHALL 被填充为该日截面的中位数（截面中位数填充）
- **AND** 极端值 SHALL 被 winsorize 到 ±3 标准差
