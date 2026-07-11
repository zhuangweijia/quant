## ADDED Requirements

### Requirement: 模型训练 — LightGBM 跨截面分类

系统 SHALL 使用 LightGBM 多分类模型，输入为某交易日全部成分股的因子矩阵，标签为未来5日相对沪深300超额收益的3档分类（0=跑输, 1=持平, 2=跑赢）。

#### Scenario: 使用滚动窗口训练模型
- **WHEN** 用户触发模型训练或 Pipeline 调度到模型训练阶段
- **THEN** 系统 SHALL 使用 walk-forward 滚动窗口划分训练集（默认训练窗口 3 年，验证窗口 6 个月）
- **AND** 标签 SHALL 为：未来5日相对收益 > +2% 标为 2（跑赢），< -2% 标为 0（跑输），其余标为 1（持平）
- **AND** 训练 SHALL 使用 LightGBM 的 `objective=multiclass`，`num_class=3`
- **AND** 训练完成后 SHALL 在验证集上计算 IC（信息系数）和 top-decile 超额收益

#### Scenario: 训练结果存储与版本管理
- **WHEN** 模型训练完成
- **THEN** 系统 SHALL 将模型文件保存到 `backend/models/` 目录，文件名格式 `model_v{N}_{date}.txt`
- **AND** SHALL 在 `model_versions` 表中记录：版本号、训练时间、训练数据范围、IC、验证集准确率、Top-3 重要特征
- **AND** 新模型 SHALL 默认不自动部署为生产模型，需用户手动确认激活

### Requirement: 模型预测 — 每日全市场评分

系统 SHALL 使用当前激活的模型版本，对最新交易日的全部成分股因子进行预测，输出每只股票的评分（0~1，越高越看好）。

#### Scenario: 每日预测生成评分
- **WHEN** Pipeline 执行到模型预测阶段
- **THEN** 系统 SHALL 加载当前激活版本的模型文件
- **AND** 输入最新交易日的因子矩阵，获取三类概率 `P(跑输)`、`P(持平)`、`P(跑赢)`
- **AND** 评分 SHALL 计算为 `score = P(跑赢) + 0.5 * P(持平)`，归一化到 [0, 1]
- **AND** 评分结果 SHALL 存入 `predictions` 表，包含 `trade_date`、`symbol`、`score`、`model_version`

#### Scenario: 无激活模型时的降级处理
- **WHEN** Pipeline 执行到预测阶段但无激活模型版本
- **THEN** 系统 SHALL 跳过预测步骤
- **AND** SHALL 通过 WebSocket 推送提示"无激活模型，请先训练并激活模型"
- **AND** 排名生成步骤 SHALL 输出空排名

### Requirement: SHAP 因素解释

系统 SHALL 使用 SHAP TreeExplainer 为每只股票的预测结果计算各因子的贡献值，并生成大白话解释。

#### Scenario: 生成个股SHAP解释
- **WHEN** 模型预测完成，为每只股票生成 SHAP 解释
- **THEN** 系统 SHALL 使用 `shap.TreeExplainer` 计算该股票各因子的 SHAP 值
- **AND** SHALL 筛选 Top 3 正向贡献因子和 Top 2 负向贡献因子
- **AND** 每个因子 SHALL 通过自然语言模板翻译为大白话（如"PE_TTM 行业分位=0.12" → "估值低于行业 88% 的公司"）
- **AND** SHAP 解释 SHALL 存入 `predictions` 表的 `explanation` JSONB 字段

#### Scenario: SHAP 解释模板覆盖全部因子类别
- **WHEN** 生成大白话解释时
- **THEN** 每个因子 SHALL 有对应的自然语言模板，按类别组织
- **AND** 动量类因子解释 SHALL 描述趋势方向（"近期动量强劲" / "近期持续下跌"）
- **AND** 估值类因子解释 SHALL 描述相对位置（"估值低于行业均值" / "估值偏高"）
- **AND** 模板 SHALL 量化关键数值（如 PE=22 时展示 "PE 22"）

### Requirement: 模型性能监控

系统 SHALL 在每次预测后记录模型预测分布，并在 IC 低于阈值时发出降级信号。

#### Scenario: 模型信号弱时的降级标记
- **WHEN** 最近 20 个交易日的滚动 IC 低于 0.02
- **THEN** 系统 SHALL 将当日预测结果标记为 `confidence=low`
- **AND** 排名表 SHALL 在前端展示"模型近期信号偏弱，排名仅供参考"提示
