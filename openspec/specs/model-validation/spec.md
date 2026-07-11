## ADDED Requirements

### Requirement: 排名分组回测验证

系统 SHALL 提供模型验证能力，基于历史排名数据模拟"按排名分组选股"策略，验证模型是否具有选股 alpha。验证 SHALL 复用现有数据库中的历史预测数据或通过 walk-forward 方式生成历史排名。

#### Scenario: 执行分组回测
- **WHEN** 用户通过 `POST /api/v1/model/backtest` 触发回测，指定时间范围和分组方式
- **THEN** 系统 SHALL 按模型历史排名将每日股票分为 5 组（quintile，每组 20%）
- **AND** SHALL 计算每组等权组合的每日收益率序列
- **AND** SHALL 计算：各组累计收益曲线、Top组-Bottom组多空收益、Top组相对沪深300超额收益、IC序列（每日排名与未来收益的 Spearman 相关）
- **AND** SHALL 输出关键指标：年化收益、最大回撤、夏普比率、IC均值、IC胜率

#### Scenario: 回测结果可视化
- **WHEN** 回测完成
- **THEN** 系统 SHALL 返回分组累计收益曲线数据（JSON），前端使用 ECharts 渲染
- **AND** SHALL 返回 IC 时间序列图数据
- **AND** SHALL 返回月度收益热力图数据

### Requirement: 模型版本对比

系统 SHALL 支持对比不同模型版本的回测表现，帮助用户决策激活哪个版本。

#### Scenario: 多版本回测对比
- **WHEN** 用户选择 2 个或更多模型版本进行回测对比
- **THEN** 系统 SHALL 对每个版本分别执行分组回测
- **AND** SHALL 返回对比表格：各版本的 IC均值、Top组年化收益、夏普比率、最大回撤
- **AND** SHALL 返回各版本 Top 组累计收益的对比曲线数据

### Requirement: 模型激活前强制验证

系统 SHALL 要求模型版本在激活前必须通过最低回测验证标准。

#### Scenario: 模型验证不达标时拒绝激活
- **WHEN** 用户尝试激活一个模型版本，但该版本从未运行过回测或回测 IC < 0.02
- **THEN** 系统 SHALL 拒绝激活，返回错误"模型验证不达标，IC 低于阈值，请先运行回测验证"
- **AND** SHALL 在错误响应中附上该版本当前的验证指标（若有）
